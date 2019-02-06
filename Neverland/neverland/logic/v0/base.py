#!/usr/bin/python3.6
#coding: utf-8

import logging

from neverland.pkt import PktTypes
from neverland.exceptions import DropPacket
from neverland.node.context import NodeContext
from neverland.logic.base import BaseLogicHandler as _BaseLogicHandler
from neverland.protocol.v0.subjects import ClusterControllingSubjects
from neverland.components.sharedmem import SharedMemoryManager


logger = logging.getLogger('Logic')


class BaseLogicHandler(_BaseLogicHandler):

    ''' The base logic handlers for protocol v0
    '''

    def __init__(self, config):
        self.config = config

        self.shm_mgr = SharedMemoryManager(self.config)

    def handle_data(self, pkt):
        pass

    def handle_ctrl(self, pkt):
        if pkt.fields.subject == ClusterControllingSubjects.RESPONSE:
            return self.handle_ctrl_response(pkt)
        else:
            return self.handle_ctrl_request(pkt)

    def handle_ctrl_request(self, pkt):
        ''' handle requests sent in CTRL packets

        This method shall be implemented in .controller.logic_handler
        '''

    def handle_ctrl_response(self, resp_pkt):
        sn = resp_pkt.fields.sn

        pkt_mgr = NodeContext.pkt_mgr
        pkt = pkt_mgr.get_pkt(sn)

        if pkt is None:
            logger.debug(f'packet manager didn\'t find pkt, sn: {sn}')
            return

        if pkt.fields.type == PktTypes.CTRL:
            if pkt.fields.subject == ClusterControllingSubjects.JOIN_CLUSTER:
                self.handle_resp_0x01_join_cluster(pkt, resp_pkt)
            if pkt.fields.subject == ClusterControllingSubjects.LEAVE_CLUSTER:
                self.handle_resp_0x02_leave_cluster(pkt, resp_pkt)

    def handle_resp_0x01_join_cluster(self, pkt, resp_pkt):
        pass

    def handle_resp_0x02_leave_cluster(self, pkt, resp_pkt):
        pass

    def handle_conn_ctrl(self, pkt):
        pass
