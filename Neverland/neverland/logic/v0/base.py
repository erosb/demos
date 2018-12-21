#!/usr/bin/python3.6
#coding: utf-8

from neverland.pkt import PktTypes
from neverland.node.context import NodeContext
from neverland.exceptions import DropPakcet
from neverland.logic.base import BaseLogicHandler as _BaseLogicHandler
from neverland.protocol.v0.subjects import ClusterControllingSubjects


class BaseLogicHandler(_BaseLogicHandler):

    ''' The base logic handlers for protocol v0
    '''

    def __init__(self, config):
        self.config = config

        self.shm_mgr = NodeContext.shm_mgr
        self.core = NodeContext.core

    def handle_data(self, pkt):
        pass

    def handle_ctrl(self, pkt):
        if pkt.fields.subject == ClusterControllingSubjects.RESPONSE:
            return self.handle_ctrl_response(pkt)
        else:
            return self.handle_ctrl_request(pkt)

    def handle_ctrl_request(self, pkt):
        pass

    def handle_ctrl_response(self, pkt):
        pass

    def handle_conn_ctrl(self, pkt):
        pass
