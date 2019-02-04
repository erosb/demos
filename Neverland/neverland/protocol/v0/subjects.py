#!/usr/bin/python3.6
#coding: utf-8

from neverland.utils import MetaEnum


class ClusterControllingSubjects(metaclass=MetaEnum):

    # This one means a node needs to join the cluster.
    # 
    # Required content: {
    #                       "identification": str,
    #                       "ip": str,
    #                       "listen_port": int,
    #                   }
    #
    # Response body: {
    #                    "permitted": bool,
    #                }
    JOIN_CLUSTER = 0x01

    # This one means a node want to detach from the cluster.
    #
    # Required content: {
    #                       "identification": str,
    #                   }
    #
    # Response body: {
    #                    "permitted": bool,
    #                }
    LEAVE_CLUSTER = 0x02

    # This one means a node needs to read some config from the controller.
    #
    # In order to make configuration management a bit easier, cluster
    # configurations shall be provided by the controller, other nodes
    # in the cluster can ask the controller for it by sending a controlling
    # packet with this subject.
    #
    # Required content: {
    #                       "identification": str,
    #                   }
    #
    # Response body: {
    #                    "": ,
    #                }
    READ_CLUSTER_CONFIG = 0x11

    # This one means the current packet contains some information about
    # cluster status.
    #
    # Only the controller node can use this subject in distributing
    # cluster status in the cluster, other nodes should not accept
    # this subject if it's not from the controller node.
    #
    # Required content: {
    #                       ""
    #                   }
    #
    # Response body: {
    #                    "identification": str,
    #                    "confirmed": bool
    #                }
    CLUSTER_STATUS_PUSHING = 0xe1

    # This one means the current packet is a response for a received request
    #
    # Required content: {
    #                       "identification": str,
    #                       "responding_sn": int,
    #                       "body": JSON,
    #                   }
    RESPONSE = 0xff
