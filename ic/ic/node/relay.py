#!/usr/bin/python3.6
#coding: utf-8


from ic.node.base import BaseNode


class RelayNode(BaseNode):

    ''' The Relay Node

    Relay nodes are the main part of the community.
    They will forward the packages to where these packages should arrive.


    Model of processes:

        master ----+----- worker
                   |
                   +----- worker
                   |
                   +----- worker
                   |
                   +----- worker


        In this model, the master process will not do anything essentially.
        All logics will be implemented in the worker. The job for the master
        is only to kill these workers when it receives SIGTERM.

        Each worker have one server socket and they should bind it to a same
        port and enable the SO_REUSEPORT option so that the kernel can do
        load balancing for them.
    '''
