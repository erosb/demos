#!/usr/bin/python3.6
#coding: utf-8

from ic.util import ObjectifiedDict


class UDPPackage(ObjectifiedDict):

    ''' The UDP Package

    Inner Data Structure:
        {
            data: bytes,
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
    '''

    def __init__(self, **kwargs):
        for kw in ['src', 'dest', 'next_hop']:
            if kw not in kwargs:
                kwargs.update(
                    {kw: {'addr': None, 'port': None}}
                )

        for key, value in kwargs.items():
            self.__dict__[key] = self.__convert(value)
