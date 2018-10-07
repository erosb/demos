#!/usr/bin/python3.6
#coding: utf-8

import unittest

import __code_path__
from ic.util import ObjectifiedDict


# Test case for ObjectifiedDict
class ODTest(unittest.TestCase):

    def test_0_set_get(self):
        od = ObjectifiedDict()
        od.a = 1
        self.assertEqual(od.a, int)
        self.assertEqual(getattr(od, 'a'), int)
        print(f'od.a = {od.a}')


if __name__ == '__main__':
    unittest.main()
