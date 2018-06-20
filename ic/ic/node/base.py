#!/usr/bin/python3.6
#coding: utf-8

import os
import select


class BaseNode():

    ''' The Base Class of Nodes

    This class contains common functionalities for all kinds of nodes.
    '''

    def __init__(self, config):
        self.config = config
        self._epoll = select.epoll()

    def run(self):
        pass

