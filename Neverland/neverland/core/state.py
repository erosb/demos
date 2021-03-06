#!/usr/bin/python3.6
#coding: utf-8

from neverland.utils import MetaEnum


class ClusterControllingStates(metaclass=MetaEnum):

    # This state means a node has just completed its initialization and
    # about to start working
    INIT = 0x00

    # This state means a node has sent out a request of joining the cluster
    # and waiting for the response
    WAITING_FOR_JOIN = 0x01

    # This state means a node has sent out a request of leaving the cluster
    # and waiting for the response
    WAITING_FOR_LEAVE = 0x02

    # This state means a node has received the response from the controller
    # and the request of joning the cluster as been permitted
    JOINED_CLUSTER = 0x11

    # This state means a node is normally working on its duty
    WORKING = 0x21
