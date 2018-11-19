#!/usr/bin/python3.6
#coding: utf-8

from neverland.pkg import FieldTypes, PkgTypes
from neverland.utils import ObjectifiedDict
from neverland.protocol.base import BaseProtocolWrapper
from neverland.exceptions import SwitchPkgFmt, InvalidPkg


UDP_DATA_LEN = 32768


class DataPkgFormat():

    ''' The format of data packages
    '''

    __type__ = PkgTypes.DATA

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

            # Each UDP package should have a serial number as its identifier.
            # (no matter which type it is)
            # The max value of an 8 bytes long integer is 18446744073709551615.
            # This means that if we send one billion packets per second then we
            # need about 585 years to make this serial overflow.
            # (2 ** 64 - 1) / (1000000000 * 3600 * 24 * 365) == 584.942417355072
            'serial': (8, FieldTypes.STRUCT_U_LONG_LONG),

            # The timestamp of the creation of the package
            'time': (8, FieldTypes.STRUCT_U_LONG_LONG),

            # Package type, 0x01 for data packages and 0x02 for controlling pkgs
            'type': (1, FieldTypes.STRUCT_U_CHAR),

            # Whether this package has been diverged,
            # 0x01 for True and 0x02 for False
            'diverged': (1, FieldTypes.STRUCT_U_CHAR),

            # The source of the package
            # TODO ipv6 support
            'src': (None if config.ipv6 else 6, FieldTypes.STRUCT_IPV4_SA),

            # The destination of the package
            # TODO ipv6 support
            'dest': (None if config.ipv6 else 6, FieldTypes.STRUCT_IPV4_SA),

            # The data
            'data': (UDP_DATA_LEN, FieldTypes.PY_BYTES),
        }


class CtrlPkgFormat():

    ''' The format of the controlling packages
    '''

    __type__ = PkgTypes.CTRL

    @classmethod
    def gen_fmt(cls, config):
        cls.__fmt__ = {
            # The first 7 fields are same as the above.
            'salt': (config.salt_len or 8, FieldTypes.PY_BYTES),
            'mac': (64, FieldTypes.PY_BYTES),
            'serial': (8, FieldTypes.STRUCT_U_LONG_LONG),
            'time': (8, FieldTypes.STRUCT_U_LONG_LONG),
            'type': (1, FieldTypes.STRUCT_U_CHAR),
            'diverged': (1, FieldTypes.STRUCT_U_CHAR),
            'src': (None if config.ipv6 else 6, FieldTypes.STRUCT_IPV4_SA),
            'dest': (None if config.ipv6 else 6, FieldTypes.STRUCT_IPV4_SA),

            # The flag of whether the iv should be changed
            # 0x01 for Ture and 0x02 for False
            'iv_changed': (1, FieldTypes.STRUCT_U_CHAR),

            # The amount of packages that can be encrypted by this iv
            'iv_duration': (8, FieldTypes.STRUCT_U_LONG_LONG),

            # The iv
            'iv': (config.iv_len or 8, FieldTypes.PY_BYTES),
        }


class ProtocolWrapper(BaseProtocolWrapper):

    def parse_udp_pkg(self, data, pkg_fmt):
        ''' override the parse_udp_pkg method

        We need to determine the type of packages.
        In this version of protocol, the first 7 fields in data packages and
        control packages are same, so we can simply look for the "type" field.

        Raise SwitchPkgFmt when we need another type of pkg_fmt.

        Well, actually, the pkg_fmt argument will always be the data_pkg_fmt.
        Once we raise the SwitchPkgFmt, the upper layer will use ctrl_pkg_fmt
        instead. Currently, we have only 2 class of pkg_fmt
        '''

        cur = 0
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

            if field_name == 'type':
                if value not in (PkgTypes.DATA, PkgTypes.CTRL):
                    raise InvalidPkg('Invalid type field')

                if value == PkgTypes.DATA and pkg_fmt.__type__ != PkgTypes.DATA:
                    raise SwitchPkgFmt('another one needed')
                if value == PkgTypes.CTRL and pkg_fmt.__type__ != PkgTypes.CTRL:
                    raise SwitchPkgFmt('another one needed')

            fields.__update__(**{field_name: value})
            cur += length

        return fields
