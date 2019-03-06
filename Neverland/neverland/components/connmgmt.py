#!/usr/bin/python3.6
#coding: utf-8


from neverland.utils import ObjectifiedDict, MetaEnum
from neverland.communicate.shm import SharedMemoryManager
from neverland.node.context import NodeContext


''' The connection management module

Nodes in the Neverland cluster shall complete a fake connection before
they start to communicate with each other.

Due to we only transport UDP packets in the cluster, so we call this connection
as "a fake connection". It's not like the TCP connection. The only thing we
need to do is send an IV to the recipient and comfirm the recipient has recived
the IV.
'''


class Connection(ObjectifiedDict):

    '''
    This class is used to contain the context of a connection.
    It's the entity what the ConnectionManager shall manage.

    Inner data structure:
        {
            "remote": {
                          "ip": str,
                          "port": int
                      },
            "status": int,
            "iv": bytes,
            "iv_duration": int
        }
    '''


class ConnStates(metaclass=MetaEnum):

    INIT = 0x00
    CONNECTING = 0x01

    CHANGING_IV = 0x11

    USABLE = 0xF0
    CLOSED = 0xFF


class ConnectionManager():

    ''' The Connection Manager

    We will store all informations of established connections in the shared
    memory. This ConnectionManager is aimed on converting these informations
    between JSONs and Connection objects. Providing Connection objects to the
    upper layer and store Connection objects in the shared memory in JSONs.

    As a manager, it should provide functionalities of establishing connection
    and closing connection as well.
    '''

    SHM_SOCKET_NAME_TEMPLATE = 'SHM-ConnectionManager-%d.socket'

    # The SHM container to store established connections.
    #
    # Data structure:
    #     {
    #         "ip:port": {
    #             "status": int,
    #             "iv": b64encode(iv),
    #             "iv_duration": int,
    #         }
    #     }
    SHM_KEY_TMP_CONNS = 'ConnectionManager-%d_Conns'

    def __init__(self, config):
        self.config = config

        self.pid = NodeContext.pid

    def init_shm(self):
        ''' initialize the shared memory manager
        '''

        self.shm_mgr = SharedMemoryManager(self.config)
        self.shm_mgr.connect(
            self.SHM_SOCKET_NAME_TEMPLATE % self.pid
        )

        self.shm_key_conns = self.SHM_KEY_TMP_CONNS % self.pid

    def connect(self, remote):
        ''' establish a connection

        :param remote: remote socket address, (ip, port)
        '''

    def disconnect(self, remote):
        ''' close a connection

        :param remote: remote socket address, (ip, port)
        '''
