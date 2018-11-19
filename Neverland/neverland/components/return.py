#!/usr/bin/python3.6
#coding: utf-8

import socket


class BaseDataReturner():

    ''' The base class of the data returners

    This kind of classes are responsible for returning packets from the
    destination server.

    Data returners are only used in the following cases:
        1. When client nodes need to send back the data from destination server
           to the application which is the source of the data.

        2. When outlet nodes need to send back the data from destination server
           to the community.
    '''

    def __init__(self, config):
        self.config = config

    def _create_return_socket(self, sa_2_bind):
        rt_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rt_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        rt_sock.setblocking(False)
        rt_sock.bind(sa_2_bind)
        return rt_sock

    def return_pkt(self, pkt):
        rt_sock = self._create_return_socket(
                      ('0.0.0.0', 0)
                  )
        rt_sock.sendto(
            pkt.data, (pkt.dest.addr, pkt.dest.port)
        )
        # It's very fast to create a new socket, so we don't need to cache it
        rt_sock.close()


class ClientDataReturner(BaseDataReturner):

    ''' Data returner class for client nodes
    '''

    def _create_return_socket(self, dest):
        rt_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rt_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # We need this socket option to bind socket on a non-local address
        rt_sock.setsockopt(socket.SOL_IP, socket.IP_TRANSPARENT, 1)

        rt_sock.setblocking(False)
        rt_sock.bind(dest)
        return rt_sock

    def return_pkt(self, pkt):
        rt_sock = self._create_return_socket(
                      (pkt.src.addr, pkt.src.port)
                  )
        rt_sock.sendto(
            pkt.data, (pkt.dest.addr, pkt.dest.port)
        )
        rt_sock.close()


class OutletDataReturner(BaseDataReturner):

    ''' Data returner class for outlet nodes
    '''
