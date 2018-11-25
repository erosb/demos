#!/usr/bin/python3.6
#coding: utf-8

from neverland.pkt import FieldTypes, PktTypes
from neverland.utils import ObjectifiedDict
from neverland.protocol.base import BaseProtocolWrapper
from neverland.exceptions import SwitchPktFmt, InvalidPkt


UDP_DATA_LEN = 65535


'''
In order to normalize the packets, we simply split them into 2 pieces.

The first one is the header, it will be fixed on the head of a packet,
it shall contain some common informations that all packets shall contain.

The second one is the body, just like body field in HTTP,
it shall contain the data we need to transfer.
'''


class HeaderFormat():

    ''' The format of packet headers
    '''

    __type__ = None

    @classmethod
    def gen_fmt(cls, config):
        cls.__fmt__ = {
            # Allows users to config it in the config file.
            # This should be unified in the community.
            'salt': (config.salt_len or 8, FieldTypes.PY_BYTES),

            # The Message Authentication Code.
            # In protocol v0, we use sha256 as the digest method,
            # so the length is fixed to 64
            'mac': (64, FieldTypes.PY_BYTES),

            # Each UDP packet should have a serial number as its identifier.
            # (no matter which type it is)
            # The max value of an 8 bytes long integer is 18446744073709551615.
            # This means that if we send one billion packets per second then we
            # need about 585 years to make this serial overflow.
            # (2 ** 64 - 1) / (1000000000 * 3600 * 24 * 365) == 584.942417355072
            'serial': (8, FieldTypes.STRUCT_U_LONG_LONG),

            # The timestamp of the creation of the packet
            'time': (8, FieldTypes.STRUCT_U_LONG_LONG),

            # Packet type, 0x01 for data packets and 0x02 for controlling pkts
            'type': (1, FieldTypes.STRUCT_U_CHAR),

            # Whether this packet has been diverged,
            # 0x01 for True and 0x02 for False
            'diverged': (1, FieldTypes.STRUCT_U_CHAR),

            # The source of the packet
            # TODO ipv6 support
            'src': (None if config.ipv6 else 6, FieldTypes.STRUCT_IPV4_SA),

            # The destination of the packet
            # TODO ipv6 support
            'dest': (None if config.ipv6 else 6, FieldTypes.STRUCT_IPV4_SA),
        }


class DataPktFormat():

    ''' The format of data packets' body
    '''

    __type__ = PktTypes.DATA

    @classmethod
    def gen_fmt(cls, config):
        cls.__fmt__ = {
            # The data
            'data': (UDP_DATA_LEN, FieldTypes.PY_BYTES),
        }


class CtrlPktFormat():

    ''' The format of the controlling packets'b body
    '''

    __type__ = PktTypes.Ctrl

    @classmethod
    def gen_fmt(cls, config):
        cls.__fmt__ = {
            'subject': (4, FieldTypes.STRUCT_U_INT),
            'content': (UDP_DATA_LEN, FieldTypes.PY_BYTES),
        }


class ConnCtrlPktFormat():

    ''' The format of the connection controlling packets' body
    '''

    __type__ = PktTypes.CONN_CTRL

    @classmethod
    def gen_fmt(cls, config):
        cls.__fmt__ = {
            # The flag of whether the iv should be changed
            # 0x01 for Ture and 0x02 for False
            'iv_changed': (1, FieldTypes.STRUCT_U_CHAR),

            # The amount of packets that can be encrypted by this iv
            'iv_duration': (8, FieldTypes.STRUCT_U_LONG_LONG),

            # The iv
            'iv': (config.iv_len or 8, FieldTypes.PY_BYTES),
        }


class ProtocolWrapper(BaseProtocolWrapper):
    pass
