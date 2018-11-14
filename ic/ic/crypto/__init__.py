#!/usr/bin/python3.6
# coding: utf-8

from ic.protocol.crypto.openssl import OpenSSLCryptor, load_libcrypto
from ic.utils import HashTools


openssl_ciphers = {
    cipher: OpenSSLCryptor for cipher in OpenSSLCryptor.supported_ciphers
}

supported_cipher = {}
supported_cipher.update(openssl_ciphers)


openssl_preload_func_map = {
    cipher: load_libcrypto for cipher in OpenSSLCryptor.supported_ciphers
}

preload_funcs = {}
preload_funcs.update(openssl_preload_func_map)


def preload_crypto_lib(cipher_name=None, libpath='libcrypto.so.1.1'):
    preload_func = preload_funcs.get(cipher_name)
    if not preload_func:
        raise Exception('unsupported cipher name')
    preload_func(libpath)


class Cryptor(object):

    def __init__(self, cipher_name, libpath, key, iv):
        self.libpath = libpath
        self._key = key
        self._iv = iv
        self._cipher_name = cipher_name
        self._cipher_cls = supported_cipher.get(cipher_name)

        if self._cipher_cls is None:
            raise Exception('unsupported cipher name')

        self._init_ciphers()

    def _init_ciphers(self):
        self._cipher = self._cipher_cls(
                           self._cipher_name,
                           self._key,
                           self._iv,
                           1,
                           self.libpath
                       )

        self._decipher = self._cipher_cls(
                             self._cipher_name,
                             self._key,
                             self._iv,
                             0,
                             self.libpath
                         )

    def reset(self):
        self._cipher.reset()
        self._decipher.reset()

    def encrypt(self, data):
        return self._cipher.update(data)

    def decrypt(self, data):
        return self._decipher.update(data)
