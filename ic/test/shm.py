#!/usr/bin/python3.6
#coding: utf-8

import os
import time
import shutil
import unittest

import __code_path__
from ic.utils import ObjectifiedDict
from ic.components.sharedmem import SharedMemoryManager, ContainerTypes


config = ObjectifiedDict(
             shm_socket_dir='/tmp/ic_shm_sock/',
             shm_manager_socket_name='manager',
         )


# clean the socket directory
if os.path.isdir(config.shm_socket_dir):
    shutil.rmtree(config.shm_socket_dir)
os.mkdir(config.shm_socket_dir)


KEY = 'k0'
DATA = [
    {
        'name': 'testing-list',
        'type': ContainerTypes.LIST,
        '2_create': [1, 2, 3],
        '2_remove': [1, 2],
        'remaining': 3,
        'remaining_key': 0,
    },
    {
        'name': 'testing-set',
        'type': ContainerTypes.SET,
        '2_create': [1, 2, 3],
        '2_remove': [1, 2],
        'remaining': 3,
        'remaining_key': 0,
    },
    {
        'name': 'testing-dict',
        'type': ContainerTypes.DICT,
        # '2_create': None,
        '2_create': {'a': 1, 'b': 2, 'c': 3},
        '2_remove': ['a', 'b'],
        'remaining': 3,
        'remaining_key': 'c',
    },
]


# Test case for SharedMemoryManager
class SHMTest(unittest.TestCase):

    def test_0_all_in_one(self):
        pid = os.fork()

        if pid == -1:
            raise OSError('fork failed, unable to run SharedMemoryManager')

        # run SHM worker in the child process
        elif pid == 0:
            shm_mgr = SharedMemoryManager(config)
            shm_mgr.run_as_worker()

        # send testing request in the parent process
        else:
            # wait for worker
            time.sleep(1)

            worker_pid = pid
            shm_mgr = SharedMemoryManager(config)
            shm_mgr.connect('test')
            print('conn_id: ', shm_mgr.current_connection.conn_id)
            self.assertIsInstance(shm_mgr.current_connection.conn_id, str)

            for td in DATA:
                print(f'\n==================={td["name"]}===================\n')
                resp = shm_mgr.create_key(KEY, td['type'], td['2_create'])
                print('\n-----------Create-----------')
                print(resp)
                self.assertTrue(resp.get('succeeded'))

                resp = shm_mgr.read_key(KEY)
                print('\n-----------Read-----------')
                print(resp)
                self.assertTrue(resp.get('succeeded'))

                resp = shm_mgr.remove_value(KEY, *td['2_remove'])
                print('\n-----------Remove-----------')
                print(resp)
                self.assertTrue(resp.get('succeeded'))

                resp = shm_mgr.read_key(KEY)
                print('\n-----------Read-----------')
                print(resp)
                self.assertTrue(resp.get('succeeded'))
                self.assertEqual(
                    resp.get('value')[td['remaining_key']],
                    td['remaining'],
                )

            shm_mgr.disconnect()
            self.assertEqual(shm_mgr.current_connection, None)


if __name__ == '__main__':
    unittest.main()
