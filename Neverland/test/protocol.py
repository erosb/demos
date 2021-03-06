#!/usr/bin/python3.6
#coding: utf-8

import unittest

import __code_path__
from neverland.pkt import UDPPacket, PktTypes
from neverland.utils import ObjectifiedDict
from neverland.protocol.v0 import ProtocolWrapper
from neverland.protocol.v0.fmt import (
    HeaderFormat,
    DataPktFormat,
    CtrlPktFormat,
    ConnCtrlPktFormat,
)
from neverland.node.context import NodeContext
from neverland.components.idgeneration import IDGenerator


id_generator = IDGenerator(1, 1)
NodeContext.id_generator = id_generator


json_config = {
    'net': {
        'ipv6': False,
        'crypto': {
            'salt_len': 8
        }
    }
}
config = ObjectifiedDict(**json_config)

base_wrapper = ProtocolWrapper(
                   config,
                   HeaderFormat,
                   DataPktFormat,
                   CtrlPktFormat,
                   ConnCtrlPktFormat,
               )


class PWTest(unittest.TestCase):

    def test_0_sort_calculators(self):
        fmt = HeaderFormat
        fmt.gen_fmt(config)
        fmt.sort_calculators()

        print('================== test_0_sort_calculators ==================')
        for field_name, calculator in fmt.__calc_definition__.items():
            print('--------------------------------------')
            print(f"field: {field_name}")
            print(f"calculator: {calculator}")
        print('========================= test_0 ends =======================\n')


    def test_1_wrap_unwrap(self):
        pkt = UDPPacket()
        pkt.fields = ObjectifiedDict(
                         serial=1,
                         type=PktTypes.CONN_CTRL,
                         diverged=0x01,
                         src=('127.0.0.1', 65535),
                         dest=('127.0.0.1', 65535),
                         iv_changed=0x01,
                         iv_duration=10000,
                         iv=b'iviviviviv'
                     )
        pkt.type = pkt.fields.type

        pkt = base_wrapper.wrap(pkt)
        print(pkt.data)
        print('==================\n')

        pkt1 = UDPPacket()
        # pkt1.type = 0x01
        pkt1.data = pkt.data
        pkt1 = base_wrapper.unwrap(pkt1)

        self.assertEqual(pkt1.valid, True)
        self.assertEqual(pkt1.type, PktTypes.CONN_CTRL)
        self.assertEqual(pkt1.fields.src, pkt.fields.src)
        self.assertEqual(pkt1.fields.dest, pkt.fields.dest)

        print(
            str(pkt1.fields)
        )


if __name__ == '__main__':
    unittest.main()
