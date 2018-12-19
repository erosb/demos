#!/usr/bin/python3.6
#coding: utf-8

from neverland.pkt import PktTypes
from neverland.exceptions import DropPakcet
from neverland.node.context import NodeContext
from neverland.logic.v0.base import BaseLogicHandler
from neverland.components.sharedmem import SHMContainerTypes
from neverland.protocol.v0.subjects import ClusterControllingSubjects


class ControllerLogicHandler(BaseLogicHandler):

    SHM_SOCKET_NAME_TEMPLATE = 'SHM-Controller-%d.socket'

    SHM_KEY_CLUSTER_NODES = 'CLUSTER_NODES'

    def __init__(self, *args, **kwargs):
        BaseLogicHandler.__init__(self, *args, **kwargs)

        self.identification = self.config.get('identification')
        self.node_identifications = self.config.get('cluster_nodes')

    def init_shm(self):
        ''' initialize the shared memory
        '''

        self.shm_mgr.connect(self.SHM_SOCKET_NAME % self.NodeContext.pid)
        self.shm_mgr.create_key(SHM_KEY_CLUSTER_NODES, SHMContainerTypes.DICT)

    def add_cluster_node(self, identification, ip):
        ''' add a new node into the cluster

        To do this, the controller node should add identification and ip address
        of a node into the {SHM_KEY_CLUSTER_NODES} field in the shared memory
        as a pair of key value.
        '''

        self.shm_mgr.add_value(
            self.SHM_KEY_CLUSTER_NODES,
            {identification: ip},
        )

    def remove_cluster_node(self, identification):
        self.shm_mgr.remove_value(
            self.SHM_KEY_CLUSTER_NODES,
            identification
        )

    def handle_ctrl_request(self, pkt):
        if pkt.fields.subject == ClusterControllingSubjects.JOIN_CLUSTER:
            pass
        elif pkt.fields.subject == ClusterControllingSubjects.LEAVE_CLUSTER:
            pass
        elif pkt.fields.subject == ClusterControllingSubjects.READ_CLUSTER_CONFIG:
            return self.handle_0x01_reading_config(pkt)
        else:
            raise DropPakcet

    def handle_0x01_join_cluster(self, pkt):
        ''' handle requests of joining cluster
        '''

        identification = pkt.fields.content.get('identification')
        host = self.node_identifications.get(identification)

        permitted = False if host is None else True
        content = {
            'identification': self.identification,
            'permitted': permitted,
            'responding_serial': pkt.fields.serial,
        }
        src = (NodeContext.local_ip, NodeContext.core.main_afferent.listen_port)

        pkt = UDPPacket()
        pkt.fields = ObjectifiedDict(
                         type=PktTypes.CTRL,
                         diverged=0x01,
                         src=src,
                         dest=pkt.fields.src,
                         subject=ClusterControllingSubjects.RESPONSE,
                         content=content,
                     )
        # TODO not completed yet
        pkt.next_hop = None

    def handle_0x02_leave_cluster(self, pkt):
        ''' handle requests of joining cluster
        '''

    def handle_0x11_reading_config(self, pkt):
        ''' handle requests of fetching config

        Here, the controller node sends the cluster config to other nodes
        '''
