#!/usr/bin/python3.6
#coding: utf-8


''' The connection management module

Nodes in the Neverland cluster shall complete a fake connection before
they start to communicate with each other.

Due to we only transport UDP packets in the cluster, so we call this connection
as "a fake connection". It's not like the TCP connection. The only thing we
need to do is send an IV to the recipient and comfirm the recipient has recived
the IV.
'''


class ConnectionManager():

    def __init__(self, config):
        self.config = config
