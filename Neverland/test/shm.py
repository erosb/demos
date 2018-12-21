#!/usr/bin/python3.6
#coding: utf-8

import os
import time
import signal as sig
import shutil
import unittest

import __code_path__
from neverland.utils import ObjectifiedDict
from neverland.components.sharedmem import SharedMemoryManager, SHMContainerTypes


config = ObjectifiedDict(
             shm_socket_dir='/tmp/nl_shm_sock/',
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
        'type': SHMContainerTypes.LIST,
        '2_create': [1, 2, 3],
        '2_add': [4],
        '2_remove': [1, 2, 4],
        'remaining': 3,
        'remaining_key': 0,
    },
    {
        'name': 'testing-set',
        'type': SHMContainerTypes.SET,
        '2_create': [1, 2, 3],
        '2_add': {4,},
        '2_remove': [1, 2, 4],
        'remaining': 3,
        'remaining_key': 0,
    },
    {
        'name': 'testing-dict',
        'type': SHMContainerTypes.DICT,
        # '2_create': None,
        '2_create': {'a': 1, 'b': 2, 'c': 3},
        '2_add': {'d': 4},
        '2_remove': ['a', 'b', 'd'],
        'remaining': 3,
        'remaining_key': 'c',
    },
]


worker_pid = None
shm_mgr = None


def launch_shm_worker():
    global worker_pid, shm_mgr

    pid = os.fork()

    if pid == -1:
        raise OSError('fork failed, unable to run SharedMemoryManager')

    # run SHM worker in the child process
    elif pid == 0:
        shm_mgr = SharedMemoryManager(config, sensitive=True)
        shm_mgr.run_as_worker()

    # send testing request in the parent process
    else:
        # wait for shm worker
        time.sleep(1)
        worker_pid = pid

    return pid


# Test case for SharedMemoryManager
class SHMTest(unittest.TestCase):

    def test_0_except_set(self):
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

            resp = shm_mgr.add_value(KEY, td['2_add'])
            print('\n-----------Add-----------')
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

    def test_1_set(self):
        KEY_FOR_SET = 'set_test'
        VALUE_FOR_SET = 'aaaaaaaaaaaaa'

        print('\n\n=====================set-value====================')
        shm_mgr = SharedMemoryManager(config)
        shm_mgr.connect('test_set')
        print('conn_id: ', shm_mgr.current_connection.conn_id)
        self.assertIsInstance(shm_mgr.current_connection.conn_id, str)

        resp = shm_mgr.create_key(KEY_FOR_SET, SHMContainerTypes.STR)
        self.assertTrue(resp.get('succeeded'))

        resp = shm_mgr.set_value(KEY_FOR_SET, VALUE_FOR_SET)
        self.assertTrue(resp.get('succeeded'))

        resp = shm_mgr.read_key(KEY_FOR_SET)
        self.assertTrue(resp.get('succeeded'))
        self.assertEqual(resp.get('value'), VALUE_FOR_SET)
        print(resp)

        shm_mgr.disconnect()
        self.assertEqual(shm_mgr.current_connection, None)


if __name__ == '__main__':
    pid = launch_shm_worker()

    # pid from fork
    if pid > 0:
        unittest.main()
        os.kill(worker_pid, sig.SIGKILL)
