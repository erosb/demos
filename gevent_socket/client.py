#!/usr/bin/python3
#coding: utf-8
import gevent
from gevent import socket

host = '127.0.0.1'
port = 12000
connect_seconds = 10
connect_num = 3

def connect(id_):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall('connected by XYL'.encode('utf-8'))
        print('挂起连接 - %s' % str(id_))
        gevent.sleep(connect_seconds)
        print('客户端断开连接 - %s' % str(id_))

t_list = [gevent.spawn(connect, i) for i in range(connect_num)]
gevent.joinall(t_list)
