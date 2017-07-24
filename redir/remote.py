#!/usr/bin/python3
# coding: utf-8
import socket

from server import TCPServer, UDPServer


class RemoteServerMixin():
    pass


class RemoteTCPServer(TCPServer, RemoteServerMixin):

    _is_local = False


class RemoteUDPServer(UDPServer, RemoteServerMixin):
    _is_local = False

    def handle_request(self, fd, evt):
        if fd == self._fd:
            msg = sock.recvmsg(BUFFER_SIZE, socket.CMSG_SPACE(24))
            data = msg[0]
            print(data)


def test_tcp(config_path='./remote_config.example.json'):
    server = RemoteTCPServer(config_path)
    server.run()


def test_udp(config_path='./remote_config.example.json'):
    server = RemoteUDPServer(config_path)
    server.run()


def test_conf(config_path='./remote_config.example.json'):
    server = RemoteUDPServer(config_path)
    print(type(server._config))
    print(server._config)


if __name__ == '__main__':
    test_tcp()
