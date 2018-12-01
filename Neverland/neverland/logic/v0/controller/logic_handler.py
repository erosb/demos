#!/usr/bin/python3.6
#coding: utf-8

from neverland.exceptions import DropPakcet
from neverland.logic.base import BaseLogicHandler
from neverland.protocol.v0.subjects import ClusterControllingSubjects


class ControllerLogicHandler(BaseLogicHandler):

    def handle_logic(self, pkt):
        if pkt.subject == ClusterControllingSubjects.READ_CLUSTER_CONFIG:
            return self.handle_0x01_reading_config(pkt)
        else:
            raise DropPakcet

    def handle_0x01_reading_config(self, pkt):
        ''' handle config fetching request

        Here, the controller node sends the cluster config to other nodes
        '''
