#!/usr/bin/python3.6
#coding: utf-8

import os
import time
import random
import socket
import logging

from neverland.pkt import UDPPacket
from neverland.exceptions import InvalidPkt, SharedMemoryError
from neverland.node.context import NodeContext
from neverland.components.sharedmem import (
    SharedMemoryManager,
    SHMContainerTypes,
)


# SHM container for storing special packets
# data structure:
#     {
#         sn: {
#             type: int,
#             fields: {}
#             previous_hop: [ip, port],
#             next_hop: [ip, port],
#         }
#     }
SHM_KEY_PKTS = 'SpecPktMgr_Packets'

# SHM container for storing serial numbers of packets that need
# to be sent repeatedly
# data structure:
#     [sn_0, sn_1]
SHM_KEY_PKTS_TO_REPEAT = 'SpecPktMgr_PacketsToRepeat'

# SHM container for storing the last repeat time of packets
# data structure:
#     {sn: timestamp}
SHM_KEY_LAST_REPEAT_TIME = 'SpecialPktRpter_LastRptTime'

# similar with the above, but contains the timestamp of the next repeat time
SHM_KEY_NEXT_REPEAT_TIME = 'SpecialPktRpter_NextRptTime'

# SHM container for storing how many times packets could be repeated
# data structure:
#     {sn: integer}
SHM_KEY_MAX_REPEAT_TIMES = 'SpecialPktRpter_MaxRepeatTimes'

# SHM container for storing how many times packets have been repeated
# data structure:
#     {sn: integer}
SHM_KEY_REPEATED_TIMES = 'SpecialPktRpter_RepeatedTimes'


class SpecialPacketManager():

    SHM_SOCKET_NAME_TEMPLATE = 'SHM-SpecialPacketManager-%d.socket'

    def __init__(self, config):
        self.config = config

    def init_shm(self):
        ''' initialize the shared memory manager
        '''

        self.shm_mgr = SharedMemoryManager(self.config)
        self.shm_mgr.connect(
            self.SHM_SOCKET_NAME_TEMPLATE % os.getpid()
        )
        self.shm_mgr.create_key(
            SHM_KEY_PKTS,
            SHMContainerTypes.DICT,
        )
        self.shm_mgr.create_key(
            SHM_KEY_PKTS_TO_REPEAT,
            SHMContainerTypes.LIST,
        )
        self.shm_mgr.create_key(
            SHM_KEY_LAST_REPEAT_TIME,
            SHMContainerTypes.DICT,
        )
        self.shm_mgr.create_key(
            SHM_KEY_NEXT_REPEAT_TIME,
            SHMContainerTypes.DICT,
        )
        self.shm_mgr.create_key(
            SHM_KEY_MAX_REPEAT_TIMES,
            SHMContainerTypes.DICT,
        )
        self.shm_mgr.create_key(
            SHM_KEY_REPEATED_TIMES,
            SHMContainerTypes.DICT,
        )

    def store_pkt(self, pkt, need_repeat=False, max_rpt_times=5):
        sn = pkt.fields.sn
        type_ = pkt.type
        fields = pkt.fields.__to_dict__()
        previous_hop = list(pkt.previous_hop)
        next_hop = list(pkt.next_hop)

        if sn is None:
            raise InvalidPkt(
                'Packets to be stored must contain a serial number'
            )

        value = {
            sn: {
                'type': type_
                'fields': fields,
                'previous_hop': previous_hop,
                'next_hop': next_hop,
            }
        }

        self.shm_mgr.lock_key(SHM_KEY_PKTS)
        self.shm_mgr.add_value(SHM_KEY_PKTS, value)
        self.shm_mgr.unlock_key(SHM_KEY_PKTS)

        if need_repeat:
            self.shm_mgr.add_value(SHM_KEY_PKTS_TO_REPEAT, [sn])
            self.set_pkt_max_repeat_times(sn, max_rpt_times)

    def get_pkt(self, sn):
        shm_data = self.shm_mgr.get_value(SHM_KEY_PKTS, sn)
        value = shm_data.get('value')

        if shm_value is None:
            return None

        return UDPPacket(
            type=value.get('type'),
            fields=value.get('fields'),
            previous_hop=value.get('previous_hop'),
            next_hop=value.get('next_hop'),
        )

    def remove_pkt(self, sn):
        self.cancel_repeat(sn)

        self.shm_mgr.lock_key(SHM_KEY_PKTS)
        self.shm_mgr.remove_value(SHM_KEY_PKTS, sn)
        self.shm_mgr.unlock_key(SHM_KEY_PKTS)

    def cancel_repeat(self, sn):
        self.shm_mgr.remove_value(SHM_KEY_PKTS_TO_REPEAT, sn)
        self.shm_mgr.remove_value(SHM_KEY_LAST_REPEAT_TIME, sn)
        self.shm_mgr.remove_value(SHM_KEY_NEXT_REPEAT_TIME, sn)
        self.shm_mgr.remove_value(SHM_KEY_MAX_REPEAT_TIMES, sn)
        self.shm_mgr.remove_value(SHM_KEY_REPEATED_TIMES, sn)

    def repeat_pkt(self, pkt, max_rpt_times=5):
        self.store_pkt(pkt, need_repeat=True, max_rpt_times=max_rpt_times)

    def get_repeating_sn_list(self):
        self.shm_mgr.read_key(SHM_KEY_PKTS_TO_REPEAT)
        return data.get('value')

    def set_pkt_last_repeat_time(self, sn, timestamp):
        self.shm_mgr.add_value(SHM_KEY_LAST_REPEAT_TIME, {sn: timestamp})

    def get_pkt_last_repeat_time(self, sn):
        shm_data = self.shm_mgr.get_value(SHM_KEY_LAST_REPEAT_TIME, sn)
        return shm_data.get('value')

    def set_pkt_next_repeat_time(self, sn, timestamp):
        self.shm_mgr.add_value(SHM_KEY_NEXT_REPEAT_TIME, {sn: timestamp})

    def get_pkt_next_repeat_time(self, sn):
        shm_data = self.shm_mgr.get_value(SHM_KEY_NEXT_REPEAT_TIME, sn)
        return shm_data.get('value')

    def set_pkt_max_repeat_times(self, sn, times):
        self.shm_mgr.add_value(SHM_KEY_MAX_REPEAT_TIMES, {sn: times})

    def get_pkt_max_repeat_times(self, sn):
        shm_data = self.shm_mgr.get_value(SHM_KEY_MAX_REPEAT_TIMES, sn)
        return shm_data.get('value')

    def set_pkt_repeated_times(self, sn, times):
        self.shm_mgr.add_value(SHM_KEY_REPEATED_TIMES, {sn: times})

    def get_pkt_repeated_times(self, sn):
        shm_data = self.shm_mgr.get_value(SHM_KEY_REPEATED_TIMES, sn)
        return shm_data.get('value')

    def increase_pkt_repeated_times(self, sn):
        repeated_times = self.get_pkt_repeated_times(sn)

        if repeated_times is None:
            repeated_times = 1
        else:
            repeated_times += 1

        self.set_pkt_repeated_times(sn, repeated_times)


class SpecialPacketRepeater():

    ''' The repeater for special packets

    A standalone worker for sending special packets repeatedly.
    '''

    def __init__(self, config, interval_args=(0.5, 1)):
        ''' Constructor

        :param config: the config instance
        :param interval_args: a pair of number in tuple or list format
                              that will be used in random.uniform to
                              generate a random interval time
        '''

        self.__running = False
        self.config = config
        self.interval_args = interval_args

        self.pkt_mgr = SpecialPacketManager(config)
        self.pkt_mgr.init_shm()

    def repeat_pkt(self, pkt):
        pass
        # to be continued ......

    def gen_interval(self):
        return random.uniform(*self.interval_args)

    def repeat(self, sn, pkt, current_ts):
        interval = self.gen_interval()
        next_rpt_ts = current_ts + interval

        self.repeat_pkt(pkt)
        self.pkt_mgr.set_pkt_last_repeat_time(sn, current_ts)
        self.pkt_mgr.set_pkt_next_repeat_time(sn, next_rpt_ts)
        self.pkt_mgr.increase_pkt_repeated_times(sn)

    def run(self):
        self.__running = True

        while self.__running:
            sn_list = self.pkt_mgr.get_repeating_sn_list()
            interval_to_next_poll = 0

            for sn in sn_list:
                pkt = self.pkt_mgr.get_pkt(sn)
                if pkt is None:
                    # packet removed in the interval of these 2 times of shared
                    # memory request, so we just need to skip
                    #
                    # Maybe we need to invoke remove_pkt here again to ensure
                    # that this serial number has been removed?
                    continue

                last_rpt_ts = self.pkt_mgr.get_pkt_last_repeat_time(sn)
                next_rpt_ts = self.pkt_mgr.get_pkt_next_repeat_time(sn)
                max_rpt_times = self.pkt_mgr.get_pkt_max_repeat_times(sn)
                rpted_times = self.pkt_mgr.get_pkt_repeated_times(sn)
                current_ts = time.time()

                if rpted_times >= max_rpt_times:
                    self.pkt_mgr.cancel_repeat(sn)
                elif last_rpt_ts is None or next_rpt_ts is None:
                    self.repeat(sn, pkt, current_ts)
                elif current_ts < next_rpt_ts:
                    # here, we calculate a minimum interval time that we need
                    # to sleep to the next poll
                    interval = next_rpt_ts - current_ts
                    if interval < interval_to_next_poll:
                        interval_to_next_poll = interval
                else:
                    self.repeat(sn, pkt, current_ts)

            time.sleep(interval_to_next_poll)
