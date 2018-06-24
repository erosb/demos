#!/usr/bin/python3.6
#coding: utf-8

import os

from ic.node import ROLES
from ic.afferents.udp import UDPReceiver
from ic.efferents.udp import UDPTransmitter
from ic.protocol.v0 import ProtocolWrapper
from ic.logic.client import ClientLogicHandler
from ic.logic.controller import ControllerLogicHandler
from ic.logic.outlet import OutletLogicHandler
from ic.logic.relay import RelayLogicHandler


LOGIC_HANDLER_MAPPING = {
    ROLES.client: ClientLogicHandler,
    ROLES.controller: ControllerLogicHandler,
    ROLES.outlet: OutletLogicHandler,
    ROLES.relay: RelayLogicHandler,
}


class BaseNode():

    ''' The Base Class of Nodes

    This class contains common functionalities for all kinds of nodes.
    '''

    def __init__(self, config):
        self.config = config

        self.role = None
        self.running = False

        self.afferent = UDPReceiver(config)
        self.efferent = UDPTransmitter(config)
        self.protocol_wrapper = ProtocolWrapper(config)

    def set_role(self, role):
        self.role = role
        self.logic_handler_cls = LOGIC_HANDLER_MAPPING[role]
        self.logic_handler = self.logic_handler_cls(self.config)

    def run(self):
        pass
