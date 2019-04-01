#!/usr/bin/python3.6
# coding: utf-8

from neverland.utils import HashTools
from neverland.exceptions import ArgumentError
from neverland.protocol.crypto.mode import Modes
from neverland.protocol.crypto.openssl import OpenSSLCryptor, load_libcrypto


openssl_ciphers = {
    cipher: OpenSSLCryptor for cipher in OpenSSLCryptor.supported_ciphers
}

supported_ciphers = {}
supported_ciphers.update(openssl_ciphers)


openssl_preload_func_map = {
    cipher: load_libcrypto for cipher in OpenSSLCryptor.supported_ciphers
}


preload_funcs = {}
preload_funcs.update(openssl_preload_func_map)


def preload_crypto_lib(cipher_name=None, libpath='libcrypto.so.1.1'):
    preload_func = preload_funcs.get(cipher_name)
    if preload_func is not None:
        preload_func(libpath)


class Cryptor(object):

    def __init__(self, config, key=None, iv=None):
        self.config = config

        self._cipher_name = self.config.net.crypto.cipher
        self._cipher_cls = supported_ciphers.get(self._cipher_name)

        if self._cipher_cls is None:
            raise Exception('unsupported cipher')

        if self._cipher_name.startswith('kc-'):
            self._cipher_cls.check_kernel_version()

        self._init_ciphers()

    def _init_ciphers(self):
        self._cipher = self._cipher_cls(self.config, Modes.ENCRYPTING)
        self._decipher = self._cipher_cls(self.config, Modes.DECRYPTING)

    def reset(self):
        self._cipher.reset()
        self._decipher.reset()

    def encrypt(self, data):
        return self._cipher.update(data)

    def decrypt(self, data):
        return self._decipher.update(data)
