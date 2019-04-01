#!/usr/bin/python3.6
#coding: utf-8

import os
import struct
import unittest

import __code_path__
from neverland.utils import ObjectifiedDict as OD
from neverland.protocol.crypto import Modes
from neverland.protocol.crypto.kc.aead.gcm import GCMKernelCryptor


config_json = {
    'net': {
        'crypto': {
            'password': 'a SUPER SUPER LONG AND VERY INDESCRIBABLE pASSw0rD',
            'cipher': 'kc-aes-192-gcm'
        }
    }
}
config = OD(**config_json)


data_4_test = os.urandom(40000)


gcm_cipher = GCMKernelCryptor(config, Modes.ENCRYPTING)
gcm_decipher = GCMKernelCryptor(config, Modes.DECRYPTING)


# Test case for kernel cryptors
class IDGTest(unittest.TestCase):

    def test_0_gcm(self):
        cipher_text = gcm_cipher.update(data_4_test)
        plain_text = gcm_decipher.update(cipher_text)

        print('GCM testing data length: ', len(data_4_test))
        print('GCM cipher text length: ', len(cipher_text))
        self.assertEqual(plain_text, data_4_test)


if __name__ == '__main__':
    unittest.main()
