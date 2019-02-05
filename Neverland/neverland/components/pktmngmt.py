#!/usr/bin/python3.6
#coding: utf-8

import os
import time
import random
import socket
import signal as sig
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


# The following SHM_KEY_TMP_* consts are used as string tamplates,
# an argument "pid" shall be passed to render templates into SHM keys
#
# Because of the SpecialPacketRepeater is not a shared worker, each forked node
# worker shall have its own packet repeater, so we need to distinguish the
# SHM container by the pid.

# SHM container for storing serial numbers of packets that need
# to be sent repeatedly
# data structure:
#     [sn_0, sn_1]
SHM_KEY_TMP_PKTS_TO_REPEAT = 'SpecPktRpter-%(pid)d_PacketsToRepeat'

# SHM container for storing the last repeat time of packets
# data structure:
#     {sn: timestamp}
SHM_KEY_TMP_LAST_REPEAT_TIME = 'SpecialPktRpter-%(pid)d_LastRptTime'

# similar with the above one, but contains the timestamp of the next repeat time
SHM_KEY_TMP_NEXT_REPEAT_TIME = 'SpecialPktRpter-%(pid)d_NextRptTime'

# SHM container for storing how many times packets could be repeated
# data structure:
#     {sn: integer}
SHM_KEY_TMP_MAX_REPEAT_TIMES = 'SpecialPktRpter-%(pid)d_MaxRepeatTimes'

# SHM container for storing how many times packets have been repeated
# data structure:
#     {sn: integer}
SHM_KEY_TMP_REPEATED_TIMES = 'SpecialPktRpter-%(pid)d_RepeatedTimes'


class SpecialPacketManager():

    SHM_SOCKET_NAME_TEMPLATE = 'SHM-SpecialPacketManager-%d.socket'

    def __init__(self, config):
        self.config = config
        self.pid = os.getpid()

        self.shm_key_pkts = SHM_KEY_PKTS

        # These containers are for the SpecialPacketRepeater, the repeater
        # will also access special packets by the manager.
        self.shm_key_pkts_to_repeat = SHM_KEY_TMP_PKTS_TO_REPEAT % self.pid
        self.shm_key_last_repeat_time = SHM_KEY_TMP_LAST_REPEAT_TIME % self.pid
        self.shm_key_next_repeat_time = SHM_KEY_TMP_NEXT_REPEAT_TIME % self.pid
        self.shm_key_max_repeat_times = SHM_KEY_TMP_MAX_REPEAT_TIMES % self.pid
        self.shm_key_repeated_times = SHM_KEY_TMP_REPEATED_TIMES % self.pid

    def init_shm(self):
        ''' initialize the shared memory manager
        '''

        self.shm_mgr = SharedMemoryManager(self.config)
        self.shm_mgr.connect(
            self.SHM_SOCKET_NAME_TEMPLATE % os.getpid()
        )
        self.shm_mgr.create_key(
            self.shm_key_pkts,
            SHMContainerTypes.DICT,
        )
        self.shm_mgr.create_key(
            self.shm_key_pkts_to_repeat,
            SHMContainerTypes.LIST,
        )
        self.shm_mgr.create_key(
            self.shm_key_last_repeat_time,
            SHMContainerTypes.DICT,
        )
        self.shm_mgr.create_key(
            self.shm_key_next_repeat_time,
            SHMContainerTypes.DICT,
        )
        self.shm_mgr.create_key(
            self.shm_key_max_repeat_times,
            SHMContainerTypes.DICT,
        )
        self.shm_mgr.create_key(
            self.shm_key_repeated_times,
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

        self.shm_mgr.lock_key(self.shm_key_pkts)
        self.shm_mgr.add_value(self.shm_key_pkts, value)
        self.shm_mgr.unlock_key(self.shm_key_pkts)

        if need_repeat:
            self.shm_mgr.add_value(self.shm_key_pkts_to_repeat, [sn])
            self.set_pkt_max_repeat_times(sn, max_rpt_times)

    def get_pkt(self, sn):
        shm_data = self.shm_mgr.get_value(self.shm_key_pkts, sn)
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

        self.shm_mgr.lock_key(self.shm_key_pkts)
        self.shm_mgr.remove_value(self.shm_key_pkts, sn)
        self.shm_mgr.unlock_key(self.shm_key_pkts)

    def cancel_repeat(self, sn):
        self.shm_mgr.remove_value(self.shm_key_pkts_to_repeat, sn)
        self.shm_mgr.remove_value(self.shm_key_last_repeat_time, sn)
        self.shm_mgr.remove_value(self.shm_key_next_repeat_time, sn)
        self.shm_mgr.remove_value(self.shm_key_max_repeat_times, sn)
        self.shm_mgr.remove_value(self.shm_key_repeated_times, sn)

    def repeat_pkt(self, pkt, max_rpt_times=5):
        self.store_pkt(pkt, need_repeat=True, max_rpt_times=max_rpt_times)

    def get_repeating_sn_list(self):
        self.shm_mgr.read_key(self.shm_key_pkts_to_repeat)
        return data.get('value')

    def set_pkt_last_repeat_time(self, sn, timestamp):
        self.shm_mgr.add_value(self.shm_key_last_repeat_time, {sn: timestamp})

    def get_pkt_last_repeat_time(self, sn):
        shm_data = self.shm_mgr.get_value(self.shm_key_last_repeat_time, sn)
        return shm_data.get('value')

    def set_pkt_next_repeat_time(self, sn, timestamp):
        self.shm_mgr.add_value(self.shm_key_next_repeat_time, {sn: timestamp})

    def get_pkt_next_repeat_time(self, sn):
        shm_data = self.shm_mgr.get_value(self.shm_key_next_repeat_time, sn)
        return shm_data.get('value')

    def set_pkt_max_repeat_times(self, sn, times):
        self.shm_mgr.add_value(self.shm_key_max_repeat_times, {sn: times})

    def get_pkt_max_repeat_times(self, sn):
        shm_data = self.shm_mgr.get_value(self.shm_key_max_repeat_times, sn)
        return shm_data.get('value')

    def set_pkt_repeated_times(self, sn, times):
        self.shm_mgr.add_value(self.shm_key_repeated_times, {sn: times})

    def get_pkt_repeated_times(self, sn):
        shm_data = self.shm_mgr.get_value(self.shm_key_repeated_times, sn)
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

    A special worker for sending special packets repeatedly.

    Actually, the packet repeater is a part of the packet manager though
    we made it standalone, but it still work together with the packet manager.
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
        self.efferent = NodeContext.main_efferent
        self.protocol_wrapper = NodeContext.protocol_wrapper

    def shutdown(self):
        pid = NodeContext.pid
        if pid is None:
            raise RuntimeError(
                'The pid of SpecialPacketRepeater is not sotred in NodeContext'
            )

        try:
            os.kill(pid, sig.SIGTERM)
        except ProcessLookupError:
            pass

    def gen_interval(self):
        return random.uniform(*self.interval_args)

    def repeat_pkt(self, pkt):
        pkt = self.protocol_wrapper.wrap(pkt)
        self.efferent.transmit(pkt)

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
            interval_to_next_poll = 1

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
