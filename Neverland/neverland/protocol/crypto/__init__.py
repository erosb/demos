#!/usr/bin/python3.6
# coding: utf-8

from neverland.utils import HashTools
from neverland.exceptions import ArgumentError
from neverland.protocol.crypto.openssl import (
    OpenSSLCryptor,
    load_libcrypto,
    EVP_MAX_KEY_LENGTH,
    EVP_MAX_IV_LENGTH,
)


# Currently, we only implemented the OpenSSLCryptor
MAX_KEY_LEN = EVP_MAX_KEY_LENGTH
MAX_IV_LEN = EVP_MAX_IV_LENGTH


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
    if preload_func is None:
        raise Exception('unsupported cipher name')
    preload_func(libpath)


# tis enough ¯\_(ツ)_/¯
def hkdf(password, key_len=16):
    if key_len > MAX_KEY_LEN:
        raise ArgumentError('key length overflows')

    x = key_len * -1

    return HashTools.sha256(
        password.encode()
    )[x:].encode()


def hdivdf(password, iv_len=8):
    ''' Hash-based Default IV Derivation Function

    Before we establish the connection and use random IVs, we will need
    a default IV to use or we cannot establish the initial connection

    And, same as the hkdf, this is enough, we don't need something complicated.
    '''

    if iv_len > MAX_IV_LEN:
        raise ArgumentError('key length overflows')

    pwd_digest = HashTools.sha256(password.encode())
    x = iv_len * -1

    return HashTools.sha256(
        pwd_digest.encode()
    )[x:].encode()


class Cryptor(object):

    def __init__(self, config, key=None, iv=None):
        self.config = config

        self.libpath = self.config.net.crypto.lib_path

        self._password = self.config.net.crypto.password
        self._key = key or hkdf(self.password)
        self._iv = iv or hdivdf(self.password)

        self._cipher_name = self.config.net.crypto.cipher
        self._cipher_cls = supported_cipher.get(self._cipher_name)

        if self._cipher_cls is None:
            raise Exception('unsupported cipher')

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
