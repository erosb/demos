#!/usr/bin/python3.6
#coding: utf-8

from neverland.node import Roles
from neverland.node.base import BaseNode


class ClientNode(BaseNode):

    ''' The Client Node

    Client nodes are the source of the data that the community will transfer.
    They will collect data from applications, wrap and send these data to
    relay nodes in the community.


    Model of processes:

        single-main-process
    '''

    role = Roles.CLIENT
