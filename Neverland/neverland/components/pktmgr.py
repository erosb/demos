#!/usr/bin/python3.6
#coding: utf-8

from neverland.components.sharedmem import SharedMemoryManager


class SpecialPacketManager():

    SHM_SOCKET_NAME_TEMPLATE = 'SHM-SpecialPacketManager-%d.socket'

    # SHM container for containing all unhandled special packets
    # data structure:
    #     {
    #         id: {
    #             fields: {}
    #             src: (ip, port),
    #             dest: (ip, port),
    #         }
    #     }
    SHM_KEY_PKTS = 'SpecPktMgr_Packets'

    def __init__(self, config):
        self.config = config

    def init_shm(self):
        ''' initialize the shared memory manager
        '''

        self.shm_mgr = SharedMemoryManager(self.config)
        self.shm_mgr.connect(
            self.SHM_SOCKET_NAME_TEMPLATE % NodeContext.pid
        )
        self.shm_mgr.create_key(
            self.SHM_KEY_CLUSTER_NODES,
            SHMContainerTypes.DICT,
        )
