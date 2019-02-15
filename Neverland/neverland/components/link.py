#!/usr/bin/python3.6
#coding: utf-8


''' The link module

Relay nodes in the Neverland cluster will work like routers in a network.
To be organized and become a network, we need a mechanism to organize our
relay nodes.

But unlike normal routing and discovering protocol in a network, we don't
need something like OSPF or RIP because the Neverland cluster has a central
node, the controller node.

So, we configure links between nodes and we only allow nodes communicate
to others through the configured links. These links are like the cables
between routers. Nodes in the Neverland cluster shall monitor its links
and report the data of monitoring to the controller and the controller
will push these data into the cluster. Once the data of link status is
ready, we can calculate best routes through some shortest path algorithm.

And it's easy to do this monitoring by our UDP packets. We can simply send a
bunch of UDP packets to a node and calculate anything we need from the response.
'''


class LinkMonitor():

    ''' The Link Monitor

    The link monitor is aimed on monitoring the transmission quality of links.

    Monitoring items:
        max delay time of response
        min delay time of response
        average delay time of response
        packet loss rate
    '''

    def __init__(self, config):
        self.config = config
