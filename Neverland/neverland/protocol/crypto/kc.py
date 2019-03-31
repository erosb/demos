#!/usr/bin/python3.6
#coding: utf-8

import os
import socket
import platform

from neverland.excpetions import ArgumentError
from neverland.utils import HashTools
from neverland.protocol.crypto.openssl import Mods as OpensslMods


''' The kernel crypto module

Linux kernel >= 4.9 is required
'''


KC_MAX_KEY_LENGTH = 16
KC_MAX_IV_LENGTH = 12

# length of Associated Authentication Data (AAD) in AEAD
KC_MAX_AAD_LENGTH = 32


class KernalCryptor(object):

    supported_ciphers = [
        'kc-aead-aes-gcm',
    ]

    cipher_kc_type_mapping = {
        'kc-aead-aes-gcm': 'aead',
    }

    cipher_kc_name_mapping = {
        'kc-aead-aes-gcm': 'gcm(aes)',
    }

    @classmethod
    def check_kernel_version(self):
        uname = platform.uname()
        kernel_versions = uname.release.split('.')

        try:
            major_version = int(kernel_versions[0])
            minor_version = int(kernel_versions[1])
        except Exception:
            raise RuntimeError('Unrecognized kernel version')

        if major_version > 4:
            return

        if minor_version > 9:
            return

        raise RuntimeError('Unsupported kernel version')

    def __init__(self, config, mod):
        ''' Constructor

        :param config: the config
        :param mod: same as the mod parameter in OpenSSLCryptor.__init__
        '''

        self.config = config

        self.cipher_name = self.config.net.crypto.cipher
        if self.cipher_name not in self.supported_ciphers:
            raise ArgumentError(f'Unsupported cipher name: {self.cipher_name}')

        self.cipher_kc_type = self.cipher_kc_type_mapping.get(self.cipher_name)
        self.cipher_kc_name = self.cipher_kc_name_mapping.get(self.cipher_name)

        self._mod = mod
        if self._mod == OpensslMods.ENCRYPTING:
            self._op = socket.ALG_OP_ENCRYPT
        elif self._mod == OpensslMods.Decryption:
            self._op = socket.ALG_OP_DECRYPT
        else:
            raise ArgumentError(f'Invalid mod: {mod}')

        self.__passwd = self.config.net.crypto.password
        self._iv_len = self.config.net.crypto.iv_len
        self._aad_len = self.config.net.crypto.aad_len

        if self._iv_len > KC_MAX_IV_LENGTH:
            raise ArgumentError('IV length overflows')

        if slef._aad_len > KC_MAX_AAD_LENGTH:
            raise ArgumentError('AAD length overflows')

        self._key = HashTools.hkdf(self.__passwd, KC_MAX_KEY_LENGTH)
        self._iv = HashTools.hdivdf(self.__passwd, self._iv_len)

        if self.cipher_kc_type == 'aead':
            self._aead = True
        else:
            self._aead = False

        self.alg_sock = self.create_alg_sock()
        self.alg_conn = self.alg_sock.accept()

    def create_alg_sock(self):
        alg_sock = socket.socket(socket.AF_ALG, socket.SOCK_SEQPACKET)

        if self._aead:
            alg_sock.setsockopt(
                socket.SOL_ALG,
                socket.ALG_SET_AEAD_AUTHSIZE,
                None,
                self.aad_len,
            )

        alg_sock.setsockopt(socket.SOL_ALG, socket.ALG_SET_KEY, self._key)
        alg_sock.bind(
            (self.cipher_kc_type, self.cipher_kc_name)
        )

        return alg_sock

    def update(self, data):
        pass

    def clean(self):
        self.alg_conn.close()
        self.alg_sock.close()

    def reset(self):
        pass

    def __del__(self):
        self.clean()
