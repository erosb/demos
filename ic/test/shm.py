#!/usr/bin/python3.6
#coding: utf-8

import os
import time
import shutil
import unittest

import __code_path__
from ic.utils import ObjectifiedDict
from ic.components.sharedmem import SharedMemoryManager


config = ObjectifiedDict(
             shm_socket_dir='/tmp/ic_shm_sock/',
             shm_manager_socket_name='manager',
         )


# clean the socket directory
if os.path.isdir(config.shm_socket_dir):
    shutil.rmtree(config.shm_socket_dir)
os.mkdir(config.shm_socket_dir)


# Test case for SharedMemoryManager
class SHMTest(unittest.TestCase):

    def test_0_all(self):
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
            print(shm_mgr.current_connection.conn_id)

            print('----------------------\n')
            resp = shm_mgr.create_key('k0', 0x13, [1, 2, 3])
            print(resp)

            print('----------------------\n')
            resp = shm_mgr.read_key('k0')
            print(resp)


if __name__ == '__main__':
    unittest.main()
