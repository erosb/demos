#!/usr/bin/python3.6
#coding: utf-8

import os
import time
import socket


sock_e = socket.socket(socket.AF_ALG, socket.SOCK_SEQPACKET)
sock_e.bind(('aead', 'gcm(aes)'))

sock_d = socket.socket(socket.AF_ALG, socket.SOCK_SEQPACKET)
sock_d.bind(('aead', 'gcm(aes)'))


# data = 'hmmmmmmmmm' * 6000
data = 'a'
data = data.encode()

print(f'Data length: {len(data)}')

assoc = os.urandom(16)
assoclen = len(assoc)
key = os.urandom(16)
iv = os.urandom(12)
taglen = 16

msg = assoc + data

sock_e.setsockopt(socket.SOL_ALG, socket.ALG_SET_KEY, key)
sock_e.setsockopt(socket.SOL_ALG, socket.ALG_SET_AEAD_AUTHSIZE, None, assoclen)
conn_e, _ = sock_e.accept()

sock_d.setsockopt(socket.SOL_ALG, socket.ALG_SET_KEY, key)
sock_d.setsockopt(socket.SOL_ALG, socket.ALG_SET_AEAD_AUTHSIZE, None, assoclen)
conn_d, _ = sock_d.accept()


# Encrypt
t0_e = time.time()
conn_e.sendmsg_afalg([msg], op=socket.ALG_OP_ENCRYPT, iv=iv, assoclen=assoclen)
res = conn_e.recv(assoclen + len(data) + taglen)
ciphertext = res[assoclen: -taglen]
tag = res[-taglen:]
t1_e = time.time()

td_e = t1_e - t0_e
print(f'Encryption time cost: {td_e}')


# Decrypt
msg = assoc + ciphertext + tag


try:
    conn_d.sendmsg_afalg(
        [os.urandom(len(msg))],
        op=socket.ALG_OP_DECRYPT,
        iv=iv,
        assoclen=assoclen
    )

    res = conn_d.recv(len(msg) - taglen)
    plaintext0 = res[assoclen:]
except OSError as e:
    if e.args[0] == 74:
        plaintext0 = b'Bingo!'
    else:
        raise e


t0_d = time.time()
conn_d.sendmsg_afalg([msg], op=socket.ALG_OP_DECRYPT, iv=iv, assoclen=assoclen)
res = conn_d.recv(len(msg) - taglen)
plaintext1 = res[assoclen:]
t1_d = time.time()

td_d = t1_d - t0_d
print(f'Decryption time cost: {td_d}')


conn_e.close()
sock_e.close()

conn_d.close()
sock_d.close()


assert data == plaintext1


# print('\n------------------\n')
# print(ciphertext)
# print('\n------------------\n')

# print('\n------------------\n')
# print(plaintext0.decode())
# print('\n------------------\n')
# print(plaintext1.decode())
