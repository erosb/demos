#!/usr/bin/python3.6
#coding: utf-8

from ic.util import ObjectifiedDict


class UDPPackage(ObjectifiedDict):

    ''' The UDP Package

    Inner Data Structure:
        {
            valid: bool or None,
            type: str,
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

    By default, the valid field is None. It should be
    set during the unpacking if the package is from other node.

    The data field is bytes which is going to transmit or just received.

    The fields field is the data that hasn't been wrapped or has been parsed.
    '''

    def __init__(self, **kwargs):
        for kw in ['src', 'dest', 'next_hop']:
            if kw not in kwargs:
                kwargs.update(
                    {kw: {'addr': None, 'port': None}}
                )

        if 'valid' not in kwargs:
            kwargs.update(valid=None)

        for key, value in kwargs.items():
            self.__dict__[key] = self.__convert(value)
