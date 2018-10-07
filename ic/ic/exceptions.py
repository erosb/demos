#!/usr/bin/python3.6
#coding: utf-8


class PkgWrappingError(Exception):
    pass


class PkgUnwrappingError(Exception):
    pass


class SwitchPkgFmt(Exception):

    ''' Switch the package format definition

    Used in ProtocolWrapper.

    This exception means that we need to use another package format.

    Once catched this exception, the upper layer should invoke the method
    again with another package format definition.
    '''


class InvalidPkg(Exception):
    pass
