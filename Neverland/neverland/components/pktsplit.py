#!/usr/bin/python3.6
#coding: utf-8


class PacketSplitter():

    ''' The packet splitter module

    As a data transporter, Neverland must face the maximum length problem
    of UDP packets. So, here is the solution: splitting.
    '''

    def __init__(self, config):
        self.config = config

    def need_to_split(self, pkt):
        ''' check if the packet needs to be splitted
        '''

        return False

    def split(self, pkt):
        ''' split a packet

        :param pkt: the packet
        :return: a list of packets
        '''

        return [pkt]
