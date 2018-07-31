#!/usr/bin/python3.6
#coding: utf-8

import select
import socket
import struct

from ic.pkg import UDPPackage


UDP_BUFFER_SIZE = 65535


class UDPReceiver():

    ''' A normal implementation of the afferents
    '''

    EV_MASK = select.EPOLLIN

    def __init__(self, config):
        self.config = config
        self._sock = self.create_socket()
        self._fd = self._sock.fileno()
        self._epoll = select.epoll()

    def create_socket(self):
        af, type_, proto, canon, sa = socket.getaddrinfo(
                                          host=self.config.listen_addr,
                                          port=self.config.listen_port,
                                          proto=socket.SOL_UDP,
                                      )[0]

        sock = socket.socket(af, type_, proto)
        sock.setblocking(False)
        return sock

    def setsockopt(self, sock):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        return sock

    def start(self):
        self._epoll.register(self._fd, self.EV_MASK)
        self._sock.bind(
            (self.config.listen_addr, self.config.listen_port)
        )

    def stop(self):
        self._epoll.unregister(self._fd)
        self._sock.close()

    def recv(self):
        pkgs = []
        events = self._epoll.poll(POLL_TIMEOUT)

        for fd, evt in events:
            data, src = self._sock.recvfrom(UDP_BUFFER_SIZE)
            pkg = UDPPackage(
                      data=data,
                      src={'addr': src[0], 'port': src[1]}
                  )
            pkgs.append(pkg)

        return pkgs


class ClientUDPReceiver(UDPReceiver):

    def setsockopt(self, sock):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # We need these options to receive udp package and get it's
        # destination from tproxy redirect.
        sock.setsockopt(socket.SOL_IP, IP_TRANSPARENT, 1)
        sock.setsockopt(socket.SOL_IP, IP_RECVORIGDSTADDR, 1)
        return sock

    def recv(self):
        ''' receive data from tproxy redirect
        '''

        pkgs = []
        events = self._epoll.poll(POLL_TIMEOUT)

        # TODO ipv6 support
        for fd, evt in events:
            data, anc, flags, src = self._sock.recvmsg(
                                        UDP_BUFFER_SIZE,
                                        socket.CMSG_SPACE(24),
                                    )

            # get and unpack the cmsg_data field from anc
            # https://docs.python.org/3/library/socket.html#socket.socket.recvmsg
            cmsg = struct.unpack('!HHBBBB', anc[0][2][:8])

            dest_port = cmsg[1]
            dest_addr = '.'.join(
                [str(u) for u in cmsg[2:]]
            )

            pkg = UDPPackage(
                      data=data,
                      src={'addr': src[0], 'port': src[1]}
                      dest={'addr': dest_addr, 'port': dest_port}
                  )
            pkgs.append(pkg)

        return pkgs
