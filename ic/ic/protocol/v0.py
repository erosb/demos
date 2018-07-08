#!/usr/bin/python3.6
#coding: utf-8

from ic.protocol.base import BaseProtocolWrapper


UDP_DATA_LEN = 32768


class DataPkgFormat():

    ''' The format of data packages
    '''

    __fmt__ = {}

    @classmethod
    def gen_fmt(cls, config):
        cls.__fmt__ = {
            # Allows users to config it in the config file.
            # This should be unified in the community.
            'salt': config.salt_len or 8,

            # The Message Authentication Code.
            # In protocol v0, we use sha256 as the digest method,
            # so the length is fixed to 64
            'mac': 64,

            # Each UDP package should have a serial number as its identifier.
            # (no matter which type it is)
            # The max value of an 8 bytes long integer is 18446744073709551615.
            # This means that if we send one billion packets per second then we
            # need about 585 years to make this serial overflow.
            # (2 ** 64 - 1) / (1000000000 * 3600 * 24 * 365) == 584.942417355072
            'serial': 8,

            # The timestamp of the creation of the package
            'time': 8,

            # Package type, 0x01 for data packages and 0x02 for controlling pkgs
            'type': 1,

            # The source of the package
            # TODO ipv6 support
            'src': None if config.ipv6 else 6,

            # The destination of the package
            # TODO ipv6 support
            'dest': None if config.ipv6 else 6,

            # The data
            'data': UDP_DATA_LEN,
        }


class CtrlPkgFormat():

    ''' The format of the controlling packages
    '''

    __fmt__ = {}

    @classmethod
    def gen_fmt(cls, config):
        cls.__fmt__ = {
            # The first 7 fields are same as the above.
            'salt': config.salt_len or 8,
            'mac': 64,
            'serial': 8,
            'time': 8,
            'type': 1,
            'src': None if config.ipv6 else 6,
            'dest': None if config.ipv6 else 6,

            # The flag of whether the iv should be changed
            'iv_changed': 1,

            # The amount packages that can be encrypted by this iv
            'iv_duration': 8,

            # The iv
            'iv': config.iv_len or 8,
        }

class ProtocolWrapper(BaseProtocolWrapper):

    pass
