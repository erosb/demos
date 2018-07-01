#!/usr/bin/python3.6
#coding: utf-8

import os

from ic.node import ROLES
from ic.afferents.udp import UDPReceiver, ClientUDPReceiver
from ic.efferents.udp import UDPTransmitter
from ic.protocol.v0 import ProtocolWrapper
from ic.logic.client import ClientLogicHandler
from ic.logic.controller import ControllerLogicHandler
from ic.logic.outlet import OutletLogicHandler
from ic.logic.relay import RelayLogicHandler


AFFERENT_MAPPING = {
    ROLES.client: ClientLogicHandler,
    ROLES.controller: UDPReceiver,
    ROLES.outlet: UDPReceiver,
    ROLES.relay: UDPReceiver,
}
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

    def __init__(self, config, role):
        self.config = config
        self.role = role
        self.running = False

    def load_modules(self):
        self.afferent_cls = AFFERENT_MAPPING[self.role]
        self.afferent = afferent_cls(self.config)

        self.efferent = UDPTransmitter(config)

        self.protocol_wrapper = ProtocolWrapper(config)

        self.logic_handler_cls = LOGIC_HANDLER_MAPPING[self.role]
        self.logic_handler = self.logic_handler_cls(self.config)

    def run(self):
        pass
