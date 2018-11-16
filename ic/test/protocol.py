#!/usr/bin/python3.6
#coding: utf-8

import unittest

import __code_path__
from ic.pkg import UDPPackage
from ic.utils import ObjectifiedDict
from ic.protocol.v0 import ProtocolWrapper
from ic.protocol.v0 import DataPkgFormat, CtrlPkgFormat


config = ObjectifiedDict()
config.salt_len = 8
config.ipv6 = False

base_wrapper = ProtocolWrapper(config, DataPkgFormat, CtrlPkgFormat)


class PWTest(unittest.TestCase):

    def test_0_wrap_unwrap(self):
        pkg = UDPPackage()
        pkg.fields = ObjectifiedDict(
                         salt=b'a'*8,
                         mac=b'a'*64,
                         serial=1,
                         time=1,
                         type=0x02,
                         diverged=0x01,
                         src=('127.0.0.1', 65535),
                         dest=('127.0.0.1', 65535),
                         iv_changed=0x01,
                         iv_duration=10000,
                         iv=b'iviviviviv'
                     )
        pkg.type = pkg.fields.type

        pkg = base_wrapper.wrap(pkg)
        print(pkg.data)
        print('==================\n')

        pkg1 = UDPPackage()
        # pkg1.type = 0x01
        pkg1.data = pkg.data
        pkg1 = base_wrapper.unwrap(pkg1)

        self.assertEqual(pkg1.valid, True)
        self.assertEqual(pkg1.type, 0x02)
        self.assertEqual(pkg1.fields.src, pkg.fields.src)
        self.assertEqual(pkg1.fields.dest, pkg.fields.dest)

        print(
            str(pkg1.fields)
        )


if __name__ == '__main__':
    unittest.main()
