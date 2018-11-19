#!/usr/bin/python3.6
#coding: utf-8

from neverland.utils import ObjectifiedDict


class PktTypes:

    DATA = 0x01
    CTRL = 0x02


class FieldTypes:

    STRUCT_U_CHAR = 0x11
    STRUCT_U_INT = 0x12
    STRUCT_U_LONG = 0x13
    STRUCT_U_LONG_LONG = 0x14

    STRUCT_IPV4_SA = 0x31
    STRUCT_IPV6_SA = 0x32

    PY_BYTES = 0x41


class UDPPacket(ObjectifiedDict):

    ''' The UDP Packet

    Inner Data Structure:
        {
            valid: bool or None,
            type: int,
            data: bytes,
            fields: ObjectifiedDict,
            src: {
                addr: str,
                port: int,
            },
            dest: {
                addr: str,
                port: int,
            },
            next_hop: {
                addr: str,
                port: int,
            },
        }

    By default, the "valid" field is None. It should be set
    during the unpacking if the packet is from other node.

    The "data" field is bytes which is going to transmit or just received.

    The "fields" field is the data that hasn't been wrapped or has been parsed.
    '''

    def __init__(self, **kwargs):
        for kw in ['src', 'dest', 'next_hop']:
            if kw not in kwargs:
                kwargs.update(
                    {kw: {'addr': None, 'port': None}}
                )

        if 'valid' not in kwargs:
            kwargs.update(valid=None)

        ObjectifiedDict.__init__(self, **kwargs)
