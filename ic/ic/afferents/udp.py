#!/usr/bin/python3.6
#coding: utf-8

import select
import socket

from ic.pkg import UDPPackage


UDP_BUFFER_SIZE = 65535


class UDPReceiver():

    poll_events = select.EPOLLIN | select.EPOLLERR

    def __init__(self, config):
        self.config = config
        self._server_sock = self.mk_server_sock()
        self._server_fd = self._server_sock.fileno()
        self._epoll = select.epoll()

    def create_server_socket(self):
        af, type_, proto, canon, sa = socket.getaddrinfo(
                                          host=self.config.listen_addr,
                                          port=self.config.listen_port,
                                          proto=socket.SOL_UDP,
                                      )

        sock = socket.socket(af, type_, proto)
        sock.setblocking(False)
        return sock

    def setsockopt(self, sock):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        return sock

    def start(self):
        self._epoll.register(self._server_fd, self.poll_events)
        self._server_sock.bind(
            (self.config.listen_addr, self.config.listen_port)
        )

    def recv(self):
        pkgs = []
        events = self._epoll.poll(POLL_TIMEOUT)

        for fd, evt in events:
            data, src = self._server_sock.recvfrom(UDP_BUFFER_SIZE)
            pkg = UDPPackage(data=data, src_ip=src[0], src_port=src[1])
            pkgs.append(pkg)
