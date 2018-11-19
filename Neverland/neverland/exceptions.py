#!/usr/bin/python3.6
#coding: utf-8


class PktWrappingError(Exception):
    pass


class PktUnwrappingError(Exception):
    pass


class SwitchPktFmt(Exception):

    ''' Switch the packet format definition

    Used in ProtocolWrapper.

    This exception means that we need to use another packet format.

    Once catched this exception, the upper layer should invoke the method
    again with another packet format definition.
    '''


class InvalidPkt(Exception):
    pass


class AddressAlreadyInUse(Exception):
    pass


class SharedMemoryError(Exception):
    pass


class SHMWorkerNotConnected(SharedMemoryError):
    pass


class SHMWorkerConnectFailed(SharedMemoryError):
    pass


class SHMResponseTimeout(SharedMemoryError):
    pass
