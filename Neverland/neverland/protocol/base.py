#!/usr/bin/python3.6
#coding: utf-8

import os
import json
import time
import struct

from neverland.pkt import UDPPacket, PktTypes, FieldTypes
from neverland.utils import (
    HashTools,
    ObjectifiedDict,
    get_localhost_ip,
)
from neverland.node.context import NodeContext
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
             length        = <length of the field>,
             type          = <field type, enumerated in FieldTypes>,
             default       = <default value of the field>,
             calculator    = <specify a function to calculate the field>,
             calc_priority = <an integer, smaller number means higher priority>,
         )

    }

    Example of the "calculator":

        def field_calculator(pkt, header_fmt, body_fmt):
            """
            :param pkt: neverland.pkt.UDPPacket instance
            :param header_fmt: the format class of the header of current packet
            :param body_fmt: the format class of the body of current packet
            """

            ## some calculation...

            return value

    -------------------------------------------

    This kind of classes depends on the ordered dict feature which implemented
    in Python 3.6 and becomes a ture feature in Python 3.7. So this also means
    earlier versions (< 3.6) of Python interpreters will not be supported.

    And we also need define the __type__ attribute, it describes the type of
    the packet format definition. The value should be choosed from pkt.PktTypes
    '''

    __type__ = None
    __fmt__ = dict()

    # field definitions that contains a calculator,
    # sorted by the calculator priority
    __calc_definition__ = dict()

    @classmethod
    def gen_fmt(cls, config):
        ''' generate __fmt__ attribute with config

        An optional way to generate the packet format definition
        '''

    @classmethod
    def sort_calculators(cls):
        '''
        Sort field calculators by the defined priority and
        store them in cls.__calc_definition__
        '''

        def _key(item):
            definition = item[1]
            return definition.calc_priority or 0

        sorted_fmt = sorted(cls.__fmt__.items(), key=_key)

        for field_name, definition in sorted_fmt:
            if definition.calculator is not None:
                cls.__calc_definition__.update({field_name: definition})


class ComplexedFormat(BasePktFormat):

    ''' Complexed packet format

    Sometimes, we will need to combine the header format and the body format.
    '''

    def combine_fmt(self, fmt_cls):
        ''' combine a new packet format class

        Works like dict.update
        '''

        self.__fmt__.update(fmt_cls.__fmt__)


def src_calculator(pkt, header_fmt, body_fmt):
    ''' calculator for the src field
    '''

    return (NodeContext.local_ip, NodeContext.listen_port)


def sn_calculator(pkt, header_fmt, body_fmt):
    ''' calculator for the serial number field
    '''

    id_generator = NodeContext.id_generator
    if id_generator is None:
        raise RuntimeError(
            'Node modules are not ready to generate packet serial numbers'
        )

    return id_generator.gen()


def salt_calculator(pkt, header_fmt, body_fmt):
    ''' calculator for the salt field
    '''

    salt_definition = header_fmt.__fmt__.get('salt')
    salt_len = salt_definition.length
    return os.urandom(salt_len)


def mac_calculator(pkt, header_fmt, body_fmt):
    ''' calculator for calculating the mac field

    Rule of the mac calculating:
        Generally, salt field and mac field are always at the first and the second
        field in the packet header. So, by default our packets will look like:

            <salt> <mac> <other_fields>

        Here I define the default rule of mac calculating as this:

            SHA256( <salt> + <other_fields> )
    '''

    data_2_hash = pkt.byte_fields.salt

    for field_name, definition in header_fmt.__fmt__.items():
        if field_name in ('salt', 'mac'):
            continue

        byte_value = getattr(pkt.byte_fields, field_name)
        data_2_hash += byte_value

    return HashTools.sha256(data_2_hash)


def time_calculator(*_):
    ''' calculator for the time field
    '''

    return int(
        time.time() * 1000000
    )


class BaseProtocolWrapper():

    ''' The ProtocolWrapper class

    ProtocolWrappers are used in wrapping or unwrapping the packets.
    They pack the field values into bytes that can be transmitted or
    parse the received bytes into defined fields.

    Notice about the struct std-lib:
        As the Python doc says:
            Native byte order is big-endian or little-endian,
            depending on the host system.
            For example, Intel x86 and AMD64 (x86-64) are little-endian;

        Neverland is supposed to run only in x86 or x86_64 environments.
        In current implementation, we used the native packing options in
        most of invoking of strcut.pack, and it will help us to ensure
        the length of the packed bytes.

        So, in this case, current implementation of ProtocolWrappers are
        totally dependent on the hardware architecture.
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

        self._body_fmt_mapping = {
            'header': self.header_fmt,
            PktTypes.DATA: self.data_pkt_fmt,
            PktTypes.CTRL: self.ctrl_pkt_fmt,
            PktTypes.CONN_CTRL: self.conn_ctrl_pkt_fmt,
        }

        # used by self.make_udp_pkt
        self.complexed_fmt_cache = dict()

    def wrap(self, pkt):
        ''' make a valid Neverland UDP packet

        :param pkt: neverland.pkt.UDPPacket object
        :return: neverland.pkt.UDPPacket object
        '''

        _type = pkt.fields.type
        if _type is None:
            raise PktWrappingError('packet.fields.type is not specified')

        pkt_fmt = self._body_fmt_mapping.get(_type)
        if pkt_fmt is None:
            raise PktWrappingError(f'Unknown packet type: {_type}')

        pkt.type = _type

        udp_data = self.make_udp_pkt(pkt, pkt_fmt)
        pkt.data = udp_data
        return pkt

    def make_udp_pkt(self, pkt, body_fmt):
        ''' make a valid Neverland UDP packet

        During the packing, this method will put each fields into pkt.byte_fields

        :param pkt: neverland.pkt.UDPPacket object
        :param body_fmt: the format definition class of the packet body
        :return: udp_data
        '''

        udp_data = b''
        fmt_name = body_fmt.__class__.__name__

        # Here, we need combine the header format and the body format,
        # so that the calculator priority can work in both 2 format classes
        if fmt_name in self.complexed_fmt_cache:
            fmt = self.complexed_fmt_cache.get(fmt_name)
        else:
            fmt = ComplexedFormat()
            fmt.combine_fmt(self.header_fmt)
            fmt.combine_fmt(body_fmt)
            fmt.sort_calculators()

            self.complexed_fmt_cache.update({fmt_name: fmt})

        for field_name, definition in fmt.__fmt__.items():
            value = getattr(pkt.fields, field_name)

            if value is None:
                if definition.calculator is None:
                    if definition.default is not None:
                        value = definition.default
                    else:
                        raise PktWrappingError(
                            f'Field {field_name} has no value '
                            f'nor calculator or a default value'
                        )
                else:
                    # we will calculate it later by the specified calculator
                    continue

            fragment = self._pack_field(value, definition.type)
            pkt.byte_fields.__update__(**{field_name: fragment})

        for field_name, definition in fmt.__calc_definition__.items():
            value = getattr(pkt.fields, field_name)

            if value is None:
                value = definition.calculator(pkt, self.header_fmt, body_fmt)

                if value is None:
                    raise PktWrappingError(
                        f'Field {field_name}: calculator {calculator} doesn\'t '
                        f'return a valid value'
                    )

                pkt.fields.__update__(**{field_name: value})

                fragment = self._pack_field(value, definition.type)
                pkt.byte_fields.__update__(**{field_name: fragment})

        # Finally, all fields are ready. Now we can combine them into udp_data
        for field_name, definition in fmt.__fmt__.items():
            bytes_ = getattr(pkt.byte_fields, field_name)
            udp_data += bytes_

        return udp_data

    def _pack_field(self, value, field_type):
        ''' pack a single field

        :param value: value of the field
        :param field_type: type of the field, select from neverland.pkt.FieldTypes
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
            ip, port = value[0], value[1]
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
        if field_type == FieldTypes.PY_DICT:
            if isinstance(value, dict):
                data = json.dumps(value)
                return data.encode()
            elif isinstance(value, ObjectifiedDict):
                data = json.dumps(value.__to_dict__())
                return data.encode()
            else:
                raise PktWrappingError(
                    f'{type(value)} cannot be packed as PY_DICT'
                )

    def unwrap(self, pkt):
        ''' unpack a raw UDP packet

        :param pkt: neverland.pkt.UDPPacket object
        :return: neverland.pkt.UDPPacket object
        '''

        try:
            fields, byte_fields = self.parse_udp_pkt(pkt)
            pkt.fields = fields
            pkt.byte_fields = byte_fields
            pkt.type = fields.type
            pkt.valid = True
        except InvalidPkt as e:
            pkt.fields = None
            pkt.byte_fields = None
            pkt.valid = False

        return pkt

    def parse_udp_pkt(self, pkt):
        ''' parse a raw UDP packet

        :param value: value of the field
        :return: (fields, byte_fields)
        '''

        cur = 0   # cursor
        fields = ObjectifiedDict()
        byte_fields = ObjectifiedDict()

        # parse the header first
        for field_name, definition in self.header_fmt.__fmt__.items():
            field_data = pkt.data[cur: cur + definition.length]

            # Packet too short, it must be invalid
            if len(field_data) == 0:
                raise InvalidPkt('packet too short')

            try:
                value = self._unpack_field(field_data, definition.type)
            except struct.error:
                raise InvalidPkt('unpack failed')

            fields.__update__(**{field_name: value})
            byte_fields.__update__(**{field_name: field_data})
            cur += definition.length

        body_type = fields.type
        body_fmt = self._body_fmt_mapping.get(body_type)
        if body_fmt is None:
            raise InvalidPkt('invalid type')

        # parse the body
        for field_name, definition in body_fmt.__fmt__.items():
            field_data = pkt.data[cur: cur + definition.length]
            # Packet too short, it must be invalid

            if len(field_data) == 0:
                raise InvalidPkt('packet too short')

            try:
                value = self._unpack_field(field_data, definition.type)
            except struct.error:
                raise InvalidPkt('unpack failed')

            fields.__update__(**{field_name: value})
            byte_fields.__update__(**{field_name: field_data})
            cur += definition.length

        return fields, byte_fields

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
        if field_type == FieldTypes.PY_DICT:
            try:
                return json.loads(data.decode())
            except json.decoder.JSONDecodeError:
                raise InvalidPkt('failed to parse a PY_DICT field')
            except UnicodeDecodeError:
                raise InvalidPkt('failed to decode a PY_DICT field')
