#!/usr/bin/python3
import socket


server_addr = '123.123.123.123'
server_port = 60051
timeout = 3    #s

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(timeout)

s.sendto('！'.encode('utf-8'), (server_addr, server_port))
