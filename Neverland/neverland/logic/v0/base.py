#!/usr/bin/python3.6
#coding: utf-8

import logging

from neverland.pkt import PktTypes
from neverland.node.context import NodeContext
from neverland.exceptions import (
    DropPacket,
    FailedToJoinCluster,
    SuccessfullyJoinedCluster,
)
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
        ''' handle packets with type flag 0x01 DATA
        '''

    def handle_ctrl(self, pkt):
        ''' handle packets with type flag 0x02 CTRL
        '''

        if pkt.fields.subject == ClusterControllingSubjects.RESPONSE:
            return self.handle_ctrl_response(pkt)
        else:
            return self.handle_ctrl_request(pkt)

    def handle_ctrl_request(self, pkt):
        ''' handle requests sent in CTRL packets

        This method shall be implemented in .controller.logic_handler
        '''

    def handle_ctrl_response(self, resp_pkt):
        ''' handle responses sent in CTRL packets
        '''

        content = resp_pkt.fields.content
        if not isinstance(content, dict):
            return

        responding_sn = content.get('responding_sn')
        if responding_sn is None:
            return

        pkt_mgr = NodeContext.pkt_mgr
        pkt = pkt_mgr.get_pkt(responding_sn)

        if pkt is None:
            logger.debug(
                f'Packet manager can\'t find the original pkt, sn: {sn}. '
                f'Drop the response packet.'
            )
            return

        if pkt.fields.type == PktTypes.CTRL:
            if pkt.fields.subject == ClusterControllingSubjects.JOIN_CLUSTER:
                self.handle_resp_0x01_join_cluster(pkt, resp_pkt)
            if pkt.fields.subject == ClusterControllingSubjects.LEAVE_CLUSTER:
                self.handle_resp_0x02_leave_cluster(pkt, resp_pkt)

    def handle_resp_0x01_join_cluster(self, pkt, resp_pkt):
        resp_content = resp_pkt.fields.content
        resp_body = content.get('body')

        if resp_body.get('permitted'):
            raise SuccessfullyJoinedCluster
        else:
            raise FailedToJoinCluster

    def handle_resp_0x02_leave_cluster(self, pkt, resp_pkt):
        pass

    def handle_conn_ctrl(self, pkt):
        pass
