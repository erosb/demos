#!/usr/bin/python3.6
#coding: utf-8


from neverland.utils import ObjectifiedDict, MetaEnum
from neverland.components.shm import SharedMemoryManager
from neverland.node.context import NodeContext


''' The connection management module

Nodes in the Neverland cluster shall complete a fake connection before
they start to communicate with each other. Within establishing this
connection, the initiator shall send an IV to the recipient. And then,
they will use this IV in encryption. So, actually the connection is
bound with the encryption, connections are like channels with unique
IVs that link nodes into a web.


Details of connection management:
    The connection is node-to-node but not core-to-core, but all
    functionalities of communication is in the core and one node
    may have multiple cores (in multiple workers). So this means
    we need to build the connection on node layer and all core
    objects in the node shall share it.

    Due to the limitation of SharedMemoryManager's implementation,
    we cannot simply share the Cryptor object between cores.

    So the solution is sharing IV and IV duration between cores.

    At the initial stage of a node, each node have a default IV that
    derived from the password. This IV will be used to establish the
    initial connection. After it, the initial IV will be placed aside
    and the node will start to communicate with other node with the
    new IV of initial connection. Once the IV of initial connection
    exceeds its duration, next connection will be established with the
    last IV, but the last connection and its IV will not be removed
    immediately, it will be kept until the third connection is established.

    During the whole process, we will keep at most 2 connections between
    2 nodes and once the third connection is established, the first one
    will be removed. And the default IV will never be removed, it's only
    used to establish the initial connection.

    So, the mind mapping is like this:

        +------------+
        | Default IV |
        +------------+

                       +--------------+     +--------------+
                       | Slot 0       |     | Slot 1       |
         Removed       |              |     |              |      Incoming
        +--------+     |  +--------+  |     |  +--------+  |     +--------+
        | IV n-1 | <-- |  |  IV n  |  | <-- |  | IV n+1 |  | <-- | IV n+2 |
        +--------+     |  +--------+  |     |  +--------+  |     +--------+
                       |              |     |              |
                       +--------------+     +--------------+
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
            "sn": int,
            "state": int,
            "iv": bytes,
            "iv_duration": int
        }


    Field Description:
        remote: the remote socket address
        sn: the serial number of a conntion
        state: the state of the conection
        iv: the IV used in the Cryptor object of this connection
        iv_duration: number of packets that could be encrypted by this IV
                     once the iv_duration is exceeded, a new connection
                     will be established.
    '''


class ConnStates(metaclass=MetaEnum):

    ''' Connection States
    '''

    # The initial state of connection object. When a Connection object
    # completes its instantiation, the first state is INIT.
    INIT = 0x00

    # This state means a request of establishing connection has been sent
    # to the remote, and we are waiting for the response.
    ESTABLISHING = 0x01

    # This state means we have received the response of the connection
    # establishing request, and the remote has accepted the connection.
    ESTABLISHED = 0x02

    # This state means the IV of this connection has exceeds its duration and
    # a new connection is establishing. This connection will be removed soon.
    REMOVING = 0x03

    # This state means the connection has been removed.
    REMOVED = 0x04


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
