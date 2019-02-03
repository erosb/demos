#!/usr/bin/python3.6
#coding: utf-8

from neverland.pkt import UDPPacket
from neverland.exceptions import InvalidPkt
from neverland.node.context import NodeContext
from neverland.components.sharedmem import (
    SharedMemoryManager,
    SHMContainerTypes,
)


class SpecialPacketManager():

    SHM_SOCKET_NAME_TEMPLATE = 'SHM-SpecialPacketManager-%d.socket'

    # SHM container for containing all unhandled special packets
    # data structure:
    #     {
    #         id: {
    #             type: int,
    #             fields: {}
    #             previous_hop: [ip, port],
    #             next_hop: [ip, port],
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
            self.SHM_KEY_PKTS,
            SHMContainerTypes.DICT,
        )

    def store_pkt(self, pkt):
        id_ = pkt.fields.serial
        type_ = pkt.type
        fields = pkt.fields.__to_dict__()
        previous_hop = list(pkt.previous_hop)
        next_hop = list(pkt.next_hop)

        if id_ is None:
            raise InvalidPkt(
                'Packets to be stored must contain a serial number'
            )

        value = {
            id_: {
                'type': type_
                'fields': fields,
                'previous_hop': previous_hop,
                'next_hop': next_hop,
            }
        }

        self.shm_mgr.lock_key(self.SHM_KEY_PKTS)
        self.shm_mgr.add_value(self.SHM_KEY_PKTS, value)
        self.shm_mgr.unlock_key(self.SHM_KEY_PKTS)

    def get_pkt(self, pkt_id):
        shm_data = self.shm_mgr.get_value(self.SHM_KEY_PKTS, pkt_id)
        value = shm_data.get('value')

        if shm_value is None:
            return None

        return UDPPacket(
                   type=value.get('type'),
                   fields=value.get('fields'),
                   previous_hop=value.get('previous_hop'),
                   next_hop=value.get('next_hop'),
               )
