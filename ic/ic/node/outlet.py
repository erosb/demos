#!/usr/bin/python3.6
#coding: utf-8


from ic.node.base import BaseNode


class OutletNode(BaseNode):

    ''' The Outlet Node

    Outlet nodes are the outfall the community where packages from client
    nodes will get exit. They will transmit packages from client node to
    the destination server and receive responding packages from the
    destination server and send back them to they relay nodes so that
    the community can complete the communication for the client.


    Model of processes:

        master ----+----- worker
                   |
                   +----- worker
                   |
                   +----- worker
                   |
                   +----- worker


        In this model, the master process will provide some shared memory for
        workers and all task about transmission will be done by workers. The
        master process should play the role of the coordinator in this model.

        Each worker have one server socket and they should bind it to a same
        port and enable the SO_REUSEPORT option so that the kernel can do
        load balancing for them.
    '''
