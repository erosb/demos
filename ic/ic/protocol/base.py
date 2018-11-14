#!/usr/bin/python3.6
#coding: utf-8

import struct

from ic.pkg import UDPPackage, PkgTypes, FieldTypes
from ic.utils import ObjectifiedDict
from ic.exceptions import (
    PkgWrappingError,
    PkgUnwrappingError,
    InvalidPkg,
    SwitchPkgFmt,
)


class BasePkgFormat():

    ''' The format of IC UDP packages

    This kind of classes are responsible for describing the format of packages.
    It should contain a dict type attribute named as "__fmt__" which describes
    the format of packages

    The format of the __fmt__ dict:
        {
            'field_name': (length, type),  #type is listed in ic.pkg.FieldTypes
        }

    This kind of classes depends on the ordered dict feature which implemented
    in Python 3.6 and becomes a ture feature in Python 3.7. So this also means
    older Versions (< 3.6) of Python interpreters will not be supported.

    And we also need define the __type__ attribute, it describes the type of
    the package format definition. The value should be choosed from pkg.PkgTypes
    '''

    __fmt__ = None
    __type__ = None

    @classmethod
    def gen_fmt(cls, config):
        ''' generate __fmt__ attribute with config

        An optional way to generate the package format definition
        '''


class BaseProtocolWrapper():

    ''' The ProtocolWrapper class

    This kind of classes are responsible for converting the ic.pkg.UDPPackage
    object into real UDP packages (bytes) which could be a valid UDP package
    that can be forwarded by IC nodes.
    '''

    def __init__(self, config, data_pkg_fmt, ctrl_pkg_fmt):
        self.config = config
        self.data_pkg_fmt = data_pkg_fmt
        self.ctrl_pkg_fmt = ctrl_pkg_fmt

        self.data_pkg_fmt.gen_fmt(config)
        self.ctrl_pkg_fmt.gen_fmt(config)

        self._fmt_mapping = {
            PkgTypes.DATA: self.data_pkg_fmt,
            PkgTypes.CTRL: self.ctrl_pkg_fmt,
        }

    def wrap(self, pkg):
        ''' make a valid IC UDP package

        :param pkg: ic.pkg.UDPPackage object
        :return: ic.pkg.UDPPackage object
        '''

        pkg_fmt = self._fmt_mapping.get(pkg.type)
        udp_data = self.make_udp_pkg(pkg.fields, pkg_fmt)
        pkg.data = udp_data
        return pkg

    def make_udp_pkg(self, data, pkg_fmt):
        ''' make a valid IC UDP package

        :param data: the "fields" attribute of ic.pkg.UDPPackage object
        :param pkg_fmt: the format definition class
        :return: bytes
        '''

        bytes_ = b''
        for field_name, definition in pkg_fmt.__fmt__.items():
            length, type_ = definition
            value = getattr(data, field_name)
            bytes_ += self._pack(value, type_)

        return bytes_

    def _pack(self, value, field_type):
        ''' pack a single field

        :param value: value of the field
        :param field_type: type of the field, choosed from ic.pkg.FieldTypes
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
                raise PkgWrappingError(
                    f'{type(value)} cannot be packed as PY_BYTES'
                )

    def unwrap(self, pkg):
        ''' unpack a raw UDP package

        :param pkg: ic.pkg.UDPPackage object
        :return: ic.pkg.UDPPackage object
        '''

        # if the pkg type has been determined, then we simply use it,
        # otherwise we use data_pkg_fmt as default
        pkg_fmt = self._fmt_mapping.get(pkg.type) or self.data_pkg_fmt

        try:
            fields = self.parse_udp_pkg(pkg.data, pkg_fmt)
            pkg.fields = fields
            pkg.type = fields.type
            pkg.valid = True
        except InvalidPkg:
            pkg.fields = None
            pkg.valid = False
        except SwitchPkgFmt:
            pkg_fmt = self.ctrl_pkg_fmt if pkg_fmt.__type__ == PkgTypes.DATA\
                                        else self.data_pkg_fmt

            try:
                fields = self.parse_udp_pkg(pkg.data, pkg_fmt)
                pkg.fields = fields
                pkg.type = fields.type
                pkg.valid = True
            except InvalidPkg:
                pkg.fields = None
                pkg.valid = False
            except SwitchPkgFmt:
                raise RuntimeError('Too many time to switch format definition')

        return pkg

    def parse_udp_pkg(self, data, pkg_fmt):
        ''' parse a raw UDP package

        :param data: bytes
        :param pkg_fmt: the format definition class
        :return: ic.utils.ObjectifiedDict object
        '''

        cur = 0   # cursor
        fields = ObjectifiedDict()

        for field_name, definition in pkg_fmt.__fmt__.items():
            length, type_ = definition

            field_data = data[cur: cur + length]
            # Package too short, it must be invalid
            if len(field_data) == 0:
                raise InvalidPkg('package too short')

            try:
                value = self._unpack(field_data, type_)
            except struct.error:
                raise InvalidPkg('unpack failed')

            fields.__update__(**{field_name: value})
            cur += length

        return fields

    def _unpack(self, data, field_type):
        ''' unpack a single field

        :param data: bytes
        :param field_type: type of the field, choosed from ic.pkg.FieldTypes
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
