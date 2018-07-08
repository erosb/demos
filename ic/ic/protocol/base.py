#!/usr/bin/python3.6
#coding: utf-8


class BasePkgFormat():

    ''' The format of IC UDP packages

    This kind of classes are responsible for describing the format of packages.
    It should contain a dict type attribute named as "__fmt__" which describes
    the format of packages

    The format of the __fmt__ dict:
        {
            'field_name': length (Bytes),
        }

    This kind of classes depends on the ordered dict feature which implemented
    in Python 3.6 and becomes a ture feature in Python 3.7. So this also means
    older Versions (< 3.6) of Python interpreters will not be supported.
    '''

    __fmt__ = None


class BaseProtocolWrapper():

    ''' The ProtocolWrapper class

    This kind of classes are responsible for converting the ic.pkg.UDPPackage
    object into real UDP packages (bytes) which could be a valid UDP package
    that can be forwarded by IC nodes.
    '''

    def __init__(self, config):
        self.config = config

    def wrap(self, pkg):
        ''' make a valid IC UDP package

        :param pkg: ic.pkg.UDPPackage object
        :return: bytes
        '''

    def unwrap(self, pkg):
        ''' unpack a raw UDP package

        :param pkg: bytes
        :return: ic.pkg.UDPPackage object
        '''

    def make_udp_pkg(self, pkg):
        ''' make a real UDP package

        :param pkg: ic.pkg.UDPPackage object
        :return: bytes
        '''

    def parse_udp_pkg(self, pkg):
        ''' parse a real UDP package

        :param pkg: bytes
        :return: ic.pkg.UDPPackage object
        '''
