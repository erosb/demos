#!/usr/bin/python3.6
#coding: utf-8

import struct
import unittest

import __code_path__
from neverland.components.idgeneration import IDGenerator


id_generator = IDGenerator(0x01, 0x01)


generated_ids = set()


# Test case for IDGenerator
class IDGTest(unittest.TestCase):

    def test_0_gen(self):
        for _ in (range(1000000)):
            id_ = id_generator.gen()
            b2_len = len('{0:b}'.format(id_))

            self.assertEqual(b2_len, 64)
            self.assertNotIn(id_, generated_ids)

            generated_ids.add(id_)

            print(id_)
            print('{0:b}'.format(id_))
            print('----------------')



if __name__ == '__main__':
    unittest.main()
