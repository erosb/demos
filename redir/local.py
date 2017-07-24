#!/usr/bin/python3
# coding: utf-8

import select
import socket

from server import TCPServer, UDPServer


class LocalServerMixin():
    pass


class LocalTCPServer(TCPServer, LocalServerMixin):

    _is_local = True


class LocalUDPServer(UDPServer, LocalServerMixin):

    _is_local = True

    def handle_request(self, fd, evt):
        if fd == self._local_sock_fd:
            if evt & select.EPOLLIN:
                msg = sock.recvmsg(BUFFER_SIZE, socket.CMSG_SPACE(24))
                data = msg[0]
                # you may need a print here
                sock_opt = msg[1][0][2]
                sock_opt = unpack_sockopt(sock_opt)
                print(sock_opt)
        else:
            pass


def test_tcp(config_path='./local_config.example.json'):
    server = LocalTCPServer(config_path)
    server.run()


def test_udp(config_path='./local_config.example.json'):
    server = LocalUDPServer(config_path)
    server.run()

def test_conf(config_path='./local_config.example.json'):
    server = LocalUDPServer(config_path)
    print(type(server._config))
    print(server._config)

if __name__ == '__main__':
    test_tcp()
