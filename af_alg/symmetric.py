#!/usr/bin/python3.6
#coding: utf-8

import os
import time
import socket


sock_e = socket.socket(socket.AF_ALG, socket.SOCK_SEQPACKET)
sock_e.bind(('skcipher', 'cbc(aes)'))

sock_d = socket.socket(socket.AF_ALG, socket.SOCK_SEQPACKET)
sock_d.bind(('skcipher', 'cbc(aes)'))


data = 'hmmmmmmmmmmmmmmm' * 16
data = data.encode()

print(f'Data length: {len(data)}')
# print(data)
print('\n------------------------\n')

key = os.urandom(32)
iv = os.urandom(16)

sock_e.setsockopt(socket.SOL_ALG, socket.ALG_SET_KEY, key)
conn_e, _ = sock_e.accept()

sock_d.setsockopt(socket.SOL_ALG, socket.ALG_SET_KEY, key)
conn_d, _ = sock_d.accept()


# Encrypt
t0_e = time.time()
conn_e.sendmsg_afalg([data], op=socket.ALG_OP_ENCRYPT, iv=iv)
res = conn_e.recv(65535)
ciphertext = res
t1_e = time.time()

td_e = t1_e - t0_e
print(f'Encryption time cost: {td_e}')
# print(ciphertext)
print('\n------------------------\n')


t0_d = time.time()
conn_d.sendmsg_afalg([ciphertext], op=socket.ALG_OP_DECRYPT, iv=iv)
plaintext = conn_d.recv(65535)
t1_d = time.time()

td_d = t1_d - t0_d
print(f'Decryption time cost: {td_d}')
# print(plaintext)

assert plaintext == data


conn_e.close()
sock_e.close()

conn_d.close()
sock_d.close()
