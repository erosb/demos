#!/usr/bin/python3.6
#coding: utf-8


class ArgumentError(Exception):
    pass


class ConfigError(Exception):
    pass


class PktWrappingError(Exception):
    pass


class PktUnwrappingError(Exception):
    pass


class InvalidPkt(Exception):
    pass


class AddressAlreadyInUse(Exception):
    pass


class DropPakcet(Exception):

    ''' Current packet shall be dropped
    '''


class FailedToJoinCluster(Exception):
    pass


class FailedToDetachFromCluster(Exception):
    pass


class SharedMemoryError(Exception):
    pass


class SHMWorkerNotConnected(SharedMemoryError):
    pass


class SHMWorkerConnectFailed(SharedMemoryError):
    pass


class SHMResponseTimeout(SharedMemoryError):
    pass
