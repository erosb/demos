#!/usr/bin/python3.6
#coding: utf-8


from ic.node.base import BaseNode


class ControllerNode(BaseNode):

    ''' The Controller Node

    Controller node is the core of the community. Each community must have
    only one controller. The controller node will administrate the community,
    store and distribute all of key information of the community. And handle
    all things about community administration.


    Model of processes:

        master ----+----- worker
                   |
                   +----- worker
                   |
                   +----- worker
                   |
                   +----- worker


        In this model, all of key information should provided by the master
        process. Workers should ask it for these information and handle
        requests from other nodes.

        Master may distribute information proactively by push them to workers.

        Each worker have one server socket and they should bind it to a same
        port and enable the SO_REUSEPORT option so that the kernel can do
        load balancing for them.


    Alternative Model:

        single-master-process

        In this model, all logic will be implemented in the master.
        All work will be done in the master process.
    '''
