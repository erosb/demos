#!/usr/bin/python3.6
#coding: utf-8

from neverland.utils import MetaEnum


class ClusterControllingStatus(metaclass=MetaEnum):

    # This status means a node has just completed its initialization and
    # about to start working
    INIT = 0x00

    # This status means a node has sent out a request of joining the cluster
    # and waiting for the response
    WAITING_FOR_JOIN = 0x01

    # This status means a node has sent out a request of leaving the cluster
    # and waiting for the response
    WAITING_FOR_LEAVE = 0x02

    # This status means a node is normally working on its duty
    WORKING = 0x21
