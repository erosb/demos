#!/usr/bin/python3.6
#coding: utf-8


class NodeContext():

    ''' Node context container

    The global context container for the Node class.
    Simply, we can just store the context info in the class' attributes.
    '''

    # The core instance
    core = None

    # pid of the worker
    pid = None

    # local IP address
    local_ip = None
