#!/usr/bin/python3.6
#coding: utf-8


class PktWrappingError(Exception):
    pass


class PktUnwrappingError(Exception):
    pass


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
