#!/usr/bin/python3.6
#coding: utf-8

import os
import sys
import json
import select
import socket
import logging

from ic.exceptions import (
    AddressAlreadyInUse,
    SHMResponseTimeout,
    SHMWorkerNotConnected,
    SHMWorkerConnectFailed,
)
from ic.utils import MetaEnum, ObjectifiedDict, gen_uuid


''' The shared memory module

For keeping consistency of some resources, I decided to make a
special worker that aimed on processing shared resources.

This SharedMemoryManager is not only the resource managing worker but also
the resource accessing client, it plays 2 roles simultaneously.

The SharedMemoryManager worker is designed to communicate with the client
by the socket-based IPC, and it shall only support the Unix domain socket.

And it's not necessary to make this communication become encrypted. We can
simply solve the security problem by using the permission mechanism of Linux.


The protocol of communication:
    The choice of transport layer protocol is UDP. UDP is much easier to handle
    than TCP, and in the case of local communication, UDP is reliable (because
    we don't need to keep UDP packets in-sequence, and it's nearly impossible
    to loss a UDP packet in local communication).

    And because of the feature of the UDP Unix domain socket, we cannot
    simply send back responses through the socket. So we need do a fake
    connection with UDP sockets.

    Before the data accessing requests are sent out, the client needs to offer
    an unique socket name and listen on it, and the manager will send back
    responses through this socket.

    Then, we can simply transfer stringified JSON through the socket.


    JSON structures in request:

        if action in [CONNECT]:
            {
                "socket": name of the socket to recieve responses,
                "action": int,
            }

        if action in [DISCONNECT]:
            {
                "conn_id": str,
                "action": int,
            }

        if action in [CREATE]:
            {
                "conn_id": str,
                "action": int,
                "key": str,
                "type": type of the container,
                "value": optional value(s) that will be put into the container,
            }

        if action in [ADD, REMOVE]:
            {
                "conn_id": str,
                "action": int,
                "key": str,
                "value": any available type in JSON,
            }

        if action in [READ, CLEAN]:
            {
                "conn_id": str,
                "action": int,
                "key": str,
            }


    JSON structures in response:

        if action != DISCONNECT:
            {
                'succeeded': bool,
                'value': the requested value,  # sets will be responded in lists
            }

        if action == DISCONNECT:
            In this case, nothing shall be sent back.
            The connection will be removed immediately.
'''


logger = logging.getLogger('SHM')


UDP_BUFFER_SIZE = 65535

# The max blocing time at the client side of the SharedMemoryManager
SHM_MAX_BLOCKING_TIME = 2

MSG_NOT_CONNECTED = 'Not connected with SharedMemoryManager Worker yet'
MSG_CONN_FAILED = 'Failed to connect to SharedMemoryManager Worker'
MSG_INVALID_DATA = 'SharedMemoryManager didn\'t handle the request correctly'
MSG_TIMEOUT = 'SharedMemoryManager worker timeout'


class Actions(metaclass=MetaEnum):

    # create a new connection
    CONNECT = 0xf0

    # close a connection
    DISCONNECT = 0xff

    # create a new key value pair, this will override the existing value
    CREATE = 0x01

    # read value from a key
    READ = 0x02

    # add a new value into a key if the key points to a set/dict/list
    ADD = 0x03

    # completely remove a key from stored resources
    CLEAN = 0x11

    # remove a value from a key if the key points to a set/dict/list
    REMOVE = 0x12


class ContainerTypes(metaclass=MetaEnum):

    STR = 0x01
    INT = 0x02
    FLOAT = 0x03
    BOOL = 0x04

    SET = 0x11
    LIST = 0x13

    DICT = 0x21


PY_TYPE_MAPPING = {
    ContainerTypes.STR: str,
    ContainerTypes.INT: int,
    ContainerTypes.FLOAT: float,
    ContainerTypes.BOOL: bool,
    ContainerTypes.SET: set,
    ContainerTypes.LIST: list,
    ContainerTypes.DICT: dict,
}


# we need this to make JSON types compatible with Python types
# in verification and updating values
COMPATIBLE_TYPE_MAPPING = {
    ContainerTypes.STR: str,
    ContainerTypes.INT: int,
    ContainerTypes.FLOAT: float,
    ContainerTypes.BOOL: bool,
    ContainerTypes.SET: list,
    ContainerTypes.LIST: list,
    ContainerTypes.DICT: dict,
}


class Connection(ObjectifiedDict):

    ''' The connections class for SharedMemoryManager
    '''


class SharedMemoryManager():

    EV_MASK = select.EPOLLIN

    def __init__(self, config):
        self.config = config
        self.socket_dir = config.shm_socket_dir

        ## the current connection between the SharedMemoryManager worker
        self.current_connection = None

        ## attributes below are for the SharedMemoryManager worker
        self.worker_socket_path = os.path.join(
                                      self.socket_dir,
                                      self.config.shm_manager_socket_name,
                                  )

        self.__running = False

        # the resource container, all shared memories will be stored in it
        self.resources = {}

        # connection container, all established connections will be stored in it
        # structure: {connection_id: Connection}
        self.connections = {}

    def _create_socket(self, socket_path=None, blocking=False):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.setblocking(blocking)
        try:
            if socket_path is not None:
                sock.bind(socket_path)
        except OSError as err:
            if err.errno == 98:
                raise AddressAlreadyInUse(
                    f'{socket_path} is already in use, connot bind on it'
                )
            else:
                raise err

        return sock

    def gen_conn_id(self):
        return gen_uuid()

    def get_compatible_value(self, key):
        ''' make the value type become compatible with json

        currently, we just need to convert set type into lists
        '''

        value = self.resources.get(key)

        if isinstance(value, set):
            return list(value)
        else:
            return value

    def add_value(self, key, values):
        ''' add values to a container
        '''

        container = self.resources[key]
        type_ = type(container)

        if type_ is set:
            for value in values:
                container.add(value)

        if type_ is list:
            for value in values:
                container.append(value)

        if type_ is dict:
            container.update(values)

    def remove_value(self, key, *values):
        ''' remove values from a container

        :param values: multipurpose parameter, when the type is dict, it will
                       be the key of dict, otherwise, it will be the value of
                       set and list
        '''

        container = self.resources[key]
        type_ = type(container)

        if type_ in (set or list):
            for value in values:
                try:
                    container.remove(value)
                except (ValueError, KeyError):
                    pass

        if type_ is dict:
            for value in values:
                container.pop(value, None)

    def save_connection(self, conn_id, conn):
        self.connections.update(
            {conn_id: conn}
        )

    def remove_connection(self, conn_id):
        self.connections.pop(conn_id, None)

    def gen_response_json(self, conn_id, succeeded, value=None):
        return {
            'conn_id': conn_id,
            'data': {
                'succeeded': succeeded,
                'value': value,
            }
        }

    def handle_connect(self, data):
        resp_sock = data.socket
        conn_id = self.gen_conn_id()
        sock = self._create_socket()
        conn = Connection(
                   conn_id=conn_id,
                   socket=sock,
                   resp_socket=resp_sock,
               )

        self.save_connection(conn_id, conn)

        return {
            'conn_id': conn_id,
            'data': {
                'succeeded': True,
                'conn_id': conn_id,
                'value': None,
            }
        }

    def handle_disconnect(self, data):
        self.remove_connection(data.conn_id)
        return None

    def handle_create(self, data):
        key = data.key
        type_ = data.type
        value = data.value
        conn_id = data.conn_id
        compatible_type = COMPATIBLE_TYPE_MAPPING.get(type_)

        if (
            (type_ not in ContainerTypes) or
            (
                type_ in ContainerTypes and
                not isinstance(value, compatible_type)
            )
        ):
            return self.gen_response_json(conn_id=conn_id, succeeded=False)

        py_type = PY_TYPE_MAPPING.get(type_)
        container = py_type()
        self.resources.update(
            {key: container}
        )

        if value is not None:
            if type_ <= ContainerTypes.BOOL:
                self.resources[key] = value
            else:
                self.add_value(key, value)

        return self.gen_response_json(conn_id=conn_id, succeeded=True)

    def handle_read(self, data):
        conn_id = data.conn_id
        key = data.key

        return self.gen_response_json(
            conn_id=conn_id,
            succeeded=True,
            value=self.get_compatible_value(key),
        )

    def handle_add(self, data):
        key = data.key
        value = data.value
        conn_id = data.conn_id

        try:
            self.add_value(key, value)
        except (TypeError, ValueError):
            return self.gen_response_json(conn_id=conn_id, succeeded=False)
        else:
            return self.gen_response_json(conn_id=conn_id, succeeded=True)

    def handle_clean(self, data):
        key = data.key
        value = data.value
        conn_id = data.conn_id

        if key in self.resources:
            self.resources.pop(key)
            return self.gen_response_json(conn_id=conn_id, succeeded=True)
        else:
            return self.gen_response_json(conn_id=conn_id, succeeded=False)

    def handle_remove(self, data):
        key = data.key
        value = data.value
        conn_id = data.conn_id

        if key in self.resources:
            try:
                self.remove_value(key, *value)
                return self.gen_response_json(conn_id=conn_id, succeeded=True)
            except TypeError:
                pass

        return self.gen_response_json(conn_id=conn_id, succeeded=False)

    def handle_request(self, data):
        try:
            data = json.loads(data.decode('utf-8'))
            if not isinstance(data, dict):
                raise ValueError
        except (UnicodeDecodeError, ValueError):
            # If this was the package which we sent, then it could not
            # cause any of these errors, so we can simply ignore it.
            return

        data = ObjectifiedDict(**data)

        if not data.action in Actions:
            # same as above
            return

        if data.action == Actions.CONNECT:
            return handle_connect(data)
        if data.action == Actions.DISCONNECT:
            return handle_disconnect(data)
        if data.action == Actions.CREATE:
            return handle_create(data)
        if data.action == Actions.READ:
            return handle_read(data)
        if data.action == Actions.ADD:
            return handle_add(data)
        if data.action == Actions.CLEAN:
            return handle_clean(data)
        if data.action == Actions.REMOVE:
            return handle_remove(data)

    def handle_responding(resp):
        ''' handle responding

        send back the response through the given socket

        :param resp: information of the response, dict or None
                     dict structure: {
                                         "conn_id": connection ID,
                                         "data": data to send back,
                                     }
        '''

        if resp is None:
            return

        conn_id = resp['conn_id']
        conn = self.connections.get(conn_id)
        data = json.dumps(resp['data']).encode()
        conn.socket.sendto(data, conn.resp_socket)

    def run_as_worker(self):
        self._epoll = select.epoll()

        self._worker_sock = self._create_socket(self.worker_socket_path)
        self._epoll.register(self._worker_sock.fileno(), self.EV_MASK)

        self.__running = True
        while self.__running:
            events = self._epoll.poll(POLL_TIMEOUT)
            for fd, evt in events:
                if evt & select.EPOLLERR:
                    msg = 'Unexpected epoll error occurred'
                    logger.error(msg)
                    raise OSError(msg)
                elif evt & select.EPOLLIN:
                    data, address = self._worker_sock.recvfrom(UDP_BUFFER_SIZE)
                    resp = self.handle_request(data)
                    self.handle_responding(resp)

        self._worker_sock.close()
        logger.info('SharedMemoryManager Worker exited')

    def shutdown_worker(self):
        if self.__running:
            self.__running = False
        else:
            msg = 'SharedMemoryManager is not running as a worker'
            logger.error(msg)
            raise RuntimeError(msg)

    def connect(self, socket_name):
        ''' Connect to the SharedMemoryManager worker

        :param socket_name: name of the socket to receive responses
        '''

        socket_path = os.path.join(self.socket_dir, socket_name)
        sock = self._create_socket(socket_path, blocking=True)
        sock.settimeout(SHM_MAX_BLOCKING_TIME)

        data = {
            "socket": socket_name,
            "action": Actions.CONNECT,
        }
        data = json.dumps(data).encode('utf-8')
        sock.sendto(data, self.worker_socket_path)

        try:
            data, address = sock.recvfrom(UDP_BUFFER_SIZE)
            data = json.loads(data.decode('utf-8'))
            if not isinstance(data, dict):
                raise ValueError
        except socket.timeout:
            logger.error(MSG_CONN_FAILED)
            raise SHMWorkerConnectFailed(MSG_CONN_FAILED)
        except (UnicodeDecodeError, ValueError):
            logger.error(MSG_INVALID_DATA)
            sys.exit(1)

        if not data.get('succeeded'):
            logger.error(
                f'Failed to connect to the SharedMemoryManager Worker. '
                f'Worker returns: {data}'
            )
            raise SHMWorkerConnectFailed(MSG_CONN_FAILED)
        else:
            conn_id = data.get('conn_id')
            self.current_connection = Connection(
                                          socket=sock,
                                          conn_id=conn_id,
                                      )

    def disconnect(self):
        ''' disconnect from the SharedMemoryManager worker
        '''

        conn = self.current_connection
        self.send_request(
            conn_id=conn.id,
            action=Actions.DISCONNECT,
        )
        conn.socket.close()
        self.current_connection = None

    def send_request(self, **request_args):
        conn = self.current_connection
        if conn is None:
            raise SHMWorkerNotConnected(MSG_NOT_CONNECTED)

        data = json.dumps(request_args).encode('utf-8')
        conn.socket.sendto(data, self.worker_socket_path)

    def read_response(self, conn_id):
        ''' read responses from the worker

        It was designed to be blocking so that the shared memory could works
        a bit more like the true memory.
        '''

        conn = self.current_connection
        if conn is None:
            raise SHMWorkerNotConnected(MSG_NOT_CONNECTED)

        try:
            data, address = sock.recvfrom(UDP_BUFFER_SIZE)
            data = json.loads(data.decode('utf-8'))
            if not isinstance(data, dict):
                raise ValueError

            return data
        except socket.timeout:
            logger.error(MSG_TIMEOUT)
            raise SHMResponseTimeout(MSG_TIMEOUT)
        except (UnicodeDecodeError, ValueError):
            logger.error(MSG_INVALID_DATA)
            sys.exit(1)
