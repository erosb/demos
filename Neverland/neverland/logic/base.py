#!/usr/bin/python3.6
#coding: utf-8


class BaseLogicHandler():

    ''' The base class of logic handlers

    Logic handlers handle the received packets and determine where these
    packets should go and how many lanes should they use.
    '''

    def __init__(self):
        pass

    def handle_logic(self, pkt):
        pass
