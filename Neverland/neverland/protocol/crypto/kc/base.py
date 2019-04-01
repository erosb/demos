#!/usr/bin/python3.6
#coding: utf-8

import os
import socket
import platform

from neverland.excpetions import ArgumentError
from neverland.utils import HashTools
from neverland.protocol.crypto import Modes


''' The kernel crypto module

Linux kernel >= 4.9 is required
'''


_kernel_version_checked = False


class BaseKernalCryptor():

    ''' The base class of kernel cryptors
    '''

    # The minimum of required version of the Linux kernel
    KERNEL_MOJOR_VERSION = 4
    KERNEL_MINOR_VERSION = 9

    supported_ciphers = []

    _iv_len = None
    _key_len = None

    _kc_cipher_type = None
    _kc_cipher_name = None

    _aead = False

    @classmethod
    def check_kernel_version(cls):
        uname = platform.uname()
        kernel_versions = uname.release.split('.')

        try:
            major_version = int(kernel_versions[0])
            minor_version = int(kernel_versions[1])
        except Exception:
            raise RuntimeError('Unrecognized kernel version')

        if major_version > KERNEL_MOJOR_VERSION:
            return

        if minor_version > KERNEL_MINOR_VERSION:
            return

        raise RuntimeError(
            f'Unsupported kernel version, Linux Kernel >= '
            f'{KERNEL_MOJOR_VERSION}.{KERNEL_MINOR_VERSION} is required.'
        )

    def __init__(self, config, mode):
        ''' Constructor

        :param config: the config
        :param mode: the working mod of the cryptor,
                    0 to decrypting and 1 to encrypting
        '''

        self.config = config

        self.cipher_name = self.config.net.crypto.cipher
        self.__passwd = self.config.net.crypto.password
        self._mode = mode

        self.prepare()
        self.checkup()
        self.init_cryptor()

    def prepare(self):
        ''' prepare attributes before checking and initializing the cryptor

        The following attributes of the instance should get assigned here:
            self._key_len
            self._iv_len
            self._kc_cipher_type
            self._kc_cipher_name
        '''

    def checkup(self):
        ''' put verifications here
        '''

        global _kernel_version_checked

        if not _kernel_version_checked:
            BaseKernalCryptor.check_kernel_version()
            _kernel_version_checked = True

        if self.cipher_name not in self.supported_ciphers:
            raise ArgumentError(f'Unsupported cipher name: {self.cipher_name}')

        if self._mode not in Modes:
            raise ArgumentError(f'Invalid mod: {self._mode}')

        cls_name = self.__class__.__name__

        if self._key_len is None:
            raise RuntimeError(f'{cls_name}._key_len is None')

        if self._iv_len is None:
            raise RuntimeError(f'{cls_name}._iv_len is None')

        if self._kc_cipher_type is None:
            raise RuntimeError(f'{cls_name}._kc_cipher_type is None')

        if self._kc_cipher_name is None:
            raise RuntimeError(f'{cls_name}._kc_cipher_name is None')

    def init_cryptor(self):
        ''' initialization of the cryptor instance
        '''

        if self._mode == Modes.ENCRYPTING:
            self._op = socket.ALG_OP_ENCRYPT
        elif self._mode == Mods.Decryption:
            self._op = socket.ALG_OP_DECRYPT
        else:
            raise ArgumentError(f'Invalid mod: {self._mode}')

        self._key = HashTools.hkdf(self.__passwd, self._key_len)
        self._iv = HashTools.hdivdf(self.__passwd, self._iv_len)

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
            (self._kc_cipher_type, self._kc_cipher_name)
        )

        return alg_sock

    def update(self, data):
        ''' do encryption or decryption
        '''

    def clean(self):
        ''' clean/close the cryptor and release resources
        '''

        self.alg_conn.close()
        self.alg_sock.close()

    def reset(self):
        ''' reset the cryptor

        Nothing needs to be done here.
        This method is reserved for the compatibility (with OpenSSL).
        '''

    def __del__(self):
        self.clean()
