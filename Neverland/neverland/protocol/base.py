#!/usr/bin/python3.6
#coding: utf-8

import struct

from neverland.pkt import UDPPacket, PktTypes, FieldTypes
from neverland.utils import ObjectifiedDict
from neverland.exceptions import (
    PktWrappingError,
    PktUnwrappingError,
    InvalidPkt,
)


class FieldDefinition(ObjectifiedDict):
    pass


class BasePktFormat():

    ''' The format of Neverland UDP packets

    This kind of classes are responsible for describing the format of packets.
    It should contain a dict type attribute named as "__fmt__" which describes
    the format of packets

    The format of the __fmt__: {

        'field_name': ObjectifiedDict(
                          length   = <length of the field>,
                          type     = <field type, enumerated in FieldTypes>,
                          default  = <default value of the field>,
                          calc_cls = <specify a calculating class>,
                      )

    }

    This kind of classes depends on the ordered dict feature which implemented
    in Python 3.6 and becomes a ture feature in Python 3.7. So this also means
    earlier versions (< 3.6) of Python interpreters will not be supported.

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
    that can be forwarded by Neverland nodes.
    '''

    def __init__(
        self,
        config,
        header_fmt,
        data_pkt_fmt,
        ctrl_pkt_fmt,
        conn_ctrl_pkt_fmt,
    ):
        self.config = config
        self.header_fmt = header_fmt
        self.data_pkt_fmt = data_pkt_fmt
        self.ctrl_pkt_fmt = ctrl_pkt_fmt
        self.conn_ctrl_pkt_fmt = conn_ctrl_pkt_fmt

        self.header_fmt.gen_fmt(config)
        self.data_pkt_fmt.gen_fmt(config)
        self.ctrl_pkt_fmt.gen_fmt(config)
        self.conn_ctrl_pkt_fmt.gen_fmt(config)

        self._fmt_mapping = {
            'header': self.header_fmt,
            PktTypes.DATA: self.data_pkt_fmt,
            PktTypes.CTRL: self.ctrl_pkt_fmt,
            PktTypes.CONN_CTRL: self.conn_ctrl_pkt_fmt,
        }

    def wrap(self, pkt):
        ''' make a valid Neverland UDP packet

        :param pkt: neverland.pkt.UDPPacket object
        :return: neverland.pkt.UDPPacket object
        '''

        pkt_fmt = self._fmt_mapping.get(pkt.type)
        udp_data = self.make_udp_pkt(pkt.fields, pkt_fmt)
        pkt.data = udp_data
        return pkt

    def make_udp_pkt(self, data, pkt_fmt):
        ''' make a valid Neverland UDP packet

        :param data: the "fields" attribute of neverland.pkt.UDPPacket object
        :param pkt_fmt: the format definition class
        :return: bytes
        '''

        bytes_ = b''

        # make header first
        for field_name, definition in self.header_fmt.__fmt__.items():
            value = getattr(data, field_name)
            bytes_ += self._pack_field(value, definition.type)

        # then, make body
        for field_name, definition in pkt_fmt.__fmt__.items():
            value = getattr(data, field_name)
            bytes_ += self._pack_field(value, definition.type)

        return bytes_

    def _pack_field(self, value, field_type):
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

        try:
            fields = self.parse_udp_pkt(pkt.data)
            pkt.fields = fields
            pkt.type = fields.type
            pkt.valid = True
        except InvalidPkt:
            pkt.fields = None
            pkt.valid = False

        return pkt

    def parse_udp_pkt(self, data):
        ''' parse a raw UDP packet

        :param data: bytes
        :return: neverland.utils.ObjectifiedDict object
        '''

        cur = 0   # cursor
        fields = ObjectifiedDict()

        # parse the header first
        for field_name, definition in self.header_fmt.__fmt__.items():
            field_data = data[cur: cur + definition.length]

            # Packet too short, it must be invalid
            if len(field_data) == 0:
                raise InvalidPkt('packet too short')

            try:
                value = self._unpack_field(field_data, definition.type)
            except struct.error:
                raise InvalidPkt('unpack failed')

            fields.__update__(**{field_name: value})
            cur += definition.length

        body_type = fields.type
        body_fmt = self._fmt_mapping.get(body_type)
        if body_fmt is None:
            raise InvalidPkt('invalid type')

        # parse the body
        for field_name, definition in body_fmt.__fmt__.items():
            field_data = data[cur: cur + definition.length]
            # Packet too short, it must be invalid

            if len(field_data) == 0:
                raise InvalidPkt('packet too short')

            try:
                value = self._unpack_field(field_data, definition.type)
            except struct.error:
                raise InvalidPkt('unpack failed')

            fields.__update__(**{field_name: value})
            cur += definition.length

        return fields

    def _unpack_field(self, data, field_type):
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
