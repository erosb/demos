#!/usr/bin/python3.6
#coding: utf-8

import os
import socket
import platform

from neverland.excpetions import ArgumentError
from neverland.utils import HashTools
from neverland.protocol.crypto.kc.base import BaseKernalCryptor


''' The KC GCM Crypto Module

Supported algorithms:
    aes-128-gcm
    aes-192-gcm
    aes-256-gcm

Linux kernel >= 4.9 is required
'''


# According to the GCM specification,
# the IV length shall be fixed in 12 bytes (96 bits).
GCM_IV_LENGTH = 12

# length of Associated Authentication Data (AAD) in AEAD
KC_MAX_AAD_LENGTH = 32


class GCMKernalCryptor(BaseKernalCryptor):

    supported_ciphers = [
        'kc-aes-128-gcm',
        'kc-aes-192-gcm',
        'kc-aes-256-gcm',
    ]

    key_length_mapping = {
        'kc-aes-128-gcm': 16,
        'kc-aes-192-gcm': 24,
        'kc-aes-256-gcm': 32,
    }

    def prepare(self):
        self._key_len = self.key_length_mapping.get(self.cipher_name)
        self._iv_len = GCM_IV_LENGTH
        self._kc_cipher_type = 'aead'
        self._kc_cipher_name = 'gcm(aes)'

    def update(self, data):
        pass
