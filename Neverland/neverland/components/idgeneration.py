#!/usr/bin/python3.6
#coding: utf-8

import time


class IDGenerator():

    ''' The packet identifier generator for the Neverland cluster

    The neverland cluster will work like a distributed system.
    So, it's meaningful to make a unique ID for each packet.

    As a decision, I choosed the snowflake algorithm. As an adaptation,
    I slightly changed the format of the bit fields.

    Format:

        |          A - 41 bits          | B - 8 bits | C - 6 bits | D - 9 bits |
        |-------------------------------|------------|------------|------------|

        Fragment A:
            41 bits millisecond timestamp

        Fragment B:
            8 bits node serial number

        Fragment C:
            6 bits core serial number

        Fragment D:
            9 bits sequence number
    '''

    MAX_TS = 0x1ffffffffff
    MAX_NODE_ID = 0xff
    MAX_CORE_ID = 0x3f
    MAX_SEQUENCE = 0x1ff

    TS_LENGTH = 41
    NODE_ID_LENGTH = 8
    CORE_ID_LENGTH = 6
    SEQUANCE_LENGTH = 9

    def __init__(self, node_id, core_id):
        self.node_id = node_id
        self.core_id = core_id

        if self.node_id > self.MAX_NODE_ID:
            raise RuntimeError('node_id overflows')

        if self.core_id > self.MAX_CORE_ID:
            raise RuntimeError('core_id overflows')

        self.__last_ts = self._get_current_ts()
        self.__sequence = 0

    def _get_current_ts(self):
        ''' get current timestamp

        :return: returns a millisecond timestamp in int format
        '''

        ts = time.time()
        return int(ts * 1000)

    def _sleep_to_next_millisecond(self):
        target = self.__last_ts + 1 / 1000
        t2s = target - time.time()
        time.sleep(t2s)

    def _next_sequence_and_ts(self):
        ts = self._get_current_ts()

        if ts == self.__last_ts:
            if self.__sequence < self.MAX_SEQUENCE:
                self.__sequence += 1
            else:
                self._sleep_to_next_millisecond()

                ts = self._get_current_ts()
                self.__last_ts = ts
                self.__sequence = 0
        else:
            self.__sequence = 0
            self.__last_ts = ts

        return self.__sequence, self.__last_ts

    def _to_base_2_string(self, num, length):
        ''' convert numbers into base 2 format

        Within the conversion, this function will also ensure the length of
        the base-2 number. If it's too short, then zeros will be added at the
        left side of base-2 formated numbers.
        '''

        b2 = '{0:b}'.format(num)
        zero_amount = length - len(b2)

        if zero_amount < 0:
            raise RuntimeError('number overflows')

        return '0' * zero_amount + b2

    def combine(self, ts, node_id, core_id, sequence):
        ''' combine the defined bit fields
        '''

        b2 = ''.join((
                 self._to_base_2_string(ts, self.TS_LENGTH),
                 self._to_base_2_string(node_id, self.NODE_ID_LENGTH),
                 self._to_base_2_string(core_id, self.CORE_ID_LENGTH),
                 self._to_base_2_string(sequence, self.SEQUANCE_LENGTH),
             ))
        return int(b2, 2)

    def gen(self):
        ''' generate the ID
        '''

        seq, ts = self._next_sequence_and_ts()
        return self.combine(ts, self.node_id, self.core_id, seq)
