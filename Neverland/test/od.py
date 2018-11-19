#!/usr/bin/python3.6
#coding: utf-8

import json
import unittest

import __code_path__
from neverland.utils import ObjectifiedDict


# Test case for ObjectifiedDict
class ODTest(unittest.TestCase):

    def test_0_set_get(self):
        od = ObjectifiedDict()
        od.a = 1
        self.assertEqual(od.a, 1)
        self.assertEqual(getattr(od, 'a'), 1)
        print(f'od.a = {od.a}')

    def test_1_to_dict(self):
        data = {
            'a': 1,
            'b': {
                'c': 3,
                'd': False
            }
        }
        od = ObjectifiedDict(**data)
        print(od)
        print(od.__to_dict__())


if __name__ == '__main__':
    unittest.main()
