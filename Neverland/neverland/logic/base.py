#!/usr/bin/python3.6
#coding: utf-8

from neverland.pkt import PktTypes
from neverland.exceptions import DropPacket


class BaseLogicHandler():

    ''' The base class of logic handlers

    Logic handlers handle the received packets and determine where these
    packets should go and how many lanes should they use.
    '''

    def __init__(self, config):
        self.config = config

    def init_shm(self):
        ''' initialize the shared memory
        '''

    def handle_logic(self, pkt):
        if pkt.fields.type == PktTypes.DATA:
            return self.handle_data(pkt)
        elif pkt.fields.type == PktTypes.CTRL:
            return self.handle_ctrl(pkt)
        elif pkt.fields.type == PktTypes.CONN_CTRL:
            return self.handle_conn_ctrl
        else:
            raise DropPacket

    def handle_data(self, pkt):
        pass

    def handle_ctrl(self, pkt):
        pass

    def handle_conn_ctrl(self, pkt):
        pass
