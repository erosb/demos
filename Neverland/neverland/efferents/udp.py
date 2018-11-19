#!/usr/bin/python3.6
#coding: utf-8

import socket


class UDPTransmitter():

    def __init__(self, config, shared_socket=None):
        ''' Constructor

        :param config: The global config instance
        :shared_socket: Efferents can use a shared socket from other modules.
                        If the shared socket is not offered, then the
                        UDPTransmitter will create a socket itself.
        '''

        self.config = config
        if shared_socket is not None:
            self._sock = shared_socket
        else:
            self._sock = self.create_socket()
            self.setsockopt(self._sock)

    def create_socket(self):
        # TODO ipv6 support
        af, type_, proto, canon, sa = socket.getaddrinfo(
                                          host='0.0.0.0',
                                          port=0,
                                          proto=socket.SOL_UDP,
                                      )

        sock = socket.socket(af, type_, proto)
        sock.setblocking(False)
        sock.bind(sa)
        return sock

    def setsockopt(self, sock):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock

    def transmit(self, pkg):
        ''' transmit a package

        :param pkg: neverland.pkg.UDPPackage object
        '''

        self._sock.sendto(pkg.data, pkg.next_hop)
