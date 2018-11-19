#!/usr/bin/python3.6
#coding: utf-8

import struct

from neverland.pkt import UDPPacket, PktTypes, FieldTypes
from neverland.utils import ObjectifiedDict
from neverland.exceptions import (
    PktWrappingError,
    PktUnwrappingError,
    InvalidPkt,
    SwitchPktFmt,
)


class BasePktFormat():

    ''' The format of IC UDP packets

    This kind of classes are responsible for describing the format of packets.
    It should contain a dict type attribute named as "__fmt__" which describes
    the format of packets

    The format of the __fmt__ dict:
        {
            'field_name': (length, type),  #type is listed in neverland.pkt.FieldTypes
        }

    This kind of classes depends on the ordered dict feature which implemented
    in Python 3.6 and becomes a ture feature in Python 3.7. So this also means
    older Versions (< 3.6) of Python interpreters will not be supported.

    And we also need define the __type__ attribute, it describes the type of
    the packet format definition. The value should be choosed from pkt.PktTypes
    '''

    __fmt__ = None
    __type__ = None

    @classmethod
    def gen_fmt(cls, config):
        ''' generate __fmt__ attribute with config

        An optional way to generate the packet format definition
        '''


class BaseProtocolWrapper():

    ''' The ProtocolWrapper class

    This kind of classes are responsible for converting the neverland.pkt.UDPPacket
    object into real UDP packets (bytes) which could be a valid UDP packet
    that can be forwarded by IC nodes.
    '''

    def __init__(self, config, data_pkt_fmt, ctrl_pkt_fmt):
        self.config = config
        self.data_pkt_fmt = data_pkt_fmt
        self.ctrl_pkt_fmt = ctrl_pkt_fmt

        self.data_pkt_fmt.gen_fmt(config)
        self.ctrl_pkt_fmt.gen_fmt(config)

        self._fmt_mapping = {
            PktTypes.DATA: self.data_pkt_fmt,
            PktTypes.CTRL: self.ctrl_pkt_fmt,
        }

    def wrap(self, pkt):
        ''' make a valid IC UDP packet

        :param pkt: neverland.pkt.UDPPacket object
        :return: neverland.pkt.UDPPacket object
        '''

        pkt_fmt = self._fmt_mapping.get(pkt.type)
        udp_data = self.make_udp_pkt(pkt.fields, pkt_fmt)
        pkt.data = udp_data
        return pkt

    def make_udp_pkt(self, data, pkt_fmt):
        ''' make a valid IC UDP packet

        :param data: the "fields" attribute of neverland.pkt.UDPPacket object
        :param pkt_fmt: the format definition class
        :return: bytes
        '''

        bytes_ = b''
        for field_name, definition in pkt_fmt.__fmt__.items():
            length, type_ = definition
            value = getattr(data, field_name)
            bytes_ += self._pack(value, type_)

        return bytes_

    def _pack(self, value, field_type):
        ''' pack a single field

        :param value: value of the field
        :param field_type: type of the field, choosed from neverland.pkt.FieldTypes
        :return: bytes
        '''

        if field_type == FieldTypes.STRUCT_U_CHAR:
            return struct.pack('B', value)
        if field_type == FieldTypes.STRUCT_U_INT:
            return struct.pack('I', value)
        if field_type == FieldTypes.STRUCT_U_LONG:
            return struct.pack('L', value)
        if field_type == FieldTypes.STRUCT_U_LONG_LONG:
            return struct.pack('Q', value)
        if field_type == FieldTypes.STRUCT_IPV4_SA:
            # ipv4 socket address should in the following format: (ip, port)
            ip, port = value
            ip = [int(u) for u in ip.split('.')]
            return struct.pack('!BBBBH', *ip, port)
        if field_type == FieldTypes.STRUCT_IPV6_SA:
            # TODO ipv6 support
            return None
        if field_type == FieldTypes.PY_BYTES:
            if isinstance(value, bytes):
                return value
            elif isinstance(value, str):
                return value.encode()
            else:
                raise PktWrappingError(
                    f'{type(value)} cannot be packed as PY_BYTES'
                )

    def unwrap(self, pkt):
        ''' unpack a raw UDP packet

        :param pkt: neverland.pkt.UDPPacket object
        :return: neverland.pkt.UDPPacket object
        '''

        # if the pkt type has been determined, then we simply use it,
        # otherwise we use data_pkt_fmt as default
        pkt_fmt = self._fmt_mapping.get(pkt.type) or self.data_pkt_fmt

        try:
            fields = self.parse_udp_pkt(pkt.data, pkt_fmt)
            pkt.fields = fields
            pkt.type = fields.type
            pkt.valid = True
        except InvalidPkt:
            pkt.fields = None
            pkt.valid = False
        except SwitchPktFmt:
            pkt_fmt = self.ctrl_pkt_fmt if pkt_fmt.__type__ == PktTypes.DATA\
                                        else self.data_pkt_fmt

            try:
                fields = self.parse_udp_pkt(pkt.data, pkt_fmt)
                pkt.fields = fields
                pkt.type = fields.type
                pkt.valid = True
            except InvalidPkt:
                pkt.fields = None
                pkt.valid = False
            except SwitchPktFmt:
                raise RuntimeError('Too many time to switch format definition')

        return pkt

    def parse_udp_pkt(self, data, pkt_fmt):
        ''' parse a raw UDP packet

        :param data: bytes
        :param pkt_fmt: the format definition class
        :return: neverland.utils.ObjectifiedDict object
        '''

        cur = 0   # cursor
        fields = ObjectifiedDict()

        for field_name, definition in pkt_fmt.__fmt__.items():
            length, type_ = definition

            field_data = data[cur: cur + length]
            # Packet too short, it must be invalid
            if len(field_data) == 0:
                raise InvalidPkt('packet too short')

            try:
                value = self._unpack(field_data, type_)
            except struct.error:
                raise InvalidPkt('unpack failed')

            fields.__update__(**{field_name: value})
            cur += length

        return fields

    def _unpack(self, data, field_type):
        ''' unpack a single field

        :param data: bytes
        :param field_type: type of the field, choosed from neverland.pkt.FieldTypes
        :return: the unpacked value
        '''

        if field_type == FieldTypes.STRUCT_U_CHAR:
            return struct.unpack('B', data)[0]
        if field_type == FieldTypes.STRUCT_U_INT:
            return struct.unpack('I', data)[0]
        if field_type == FieldTypes.STRUCT_U_LONG:
            return struct.unpack('L', data)[0]
        if field_type == FieldTypes.STRUCT_U_LONG_LONG:
            return struct.unpack('Q', data)[0]
        if field_type == FieldTypes.STRUCT_IPV4_SA:
            info = struct.unpack('!BBBBH', data)
            ip = '.'.join(
                    [str(unit) for unit in info[0:4]]
                 )
            port = info[-1]
            return (ip, port)
        if field_type == FieldTypes.STRUCT_IPV6_SA:
            # TODO ipv6 support
            return None
        if field_type == FieldTypes.PY_BYTES:
            return data
