#!/usr/bin/python3.6
# coding: utf-8

from neverland.utils import MetaEnum


class Modes(metaclass=MetaEnum):

    ''' working mods of cryptors

    This is from OpenSSL originally.
    And it looks nice, so I use it in the whole crypto package.
    '''

    DECRYPTING = 0
    ENCRYPTING = 1
