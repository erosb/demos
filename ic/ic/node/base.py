#!/usr/bin/python3.6
#coding: utf-8

import os
import sys
import signal as sig

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

    def _handle_term(self, signal, sf):
        pid_path = self.config.pid_file
        if os.path.isfile(pid_path):
            os.remove(pid_path)
        sys.exit(0)

    def daemonize(self):
        pid = os.fork()

        if pid == -1: 
            raise OSError('Fork failed when doing daemonize')

        def quit(sg, sf):
            sys.exit(0)

        term_signals = [sig.SIGINT, sig.SIGQUIT, sig.SIGTERM]
        if pid > 0:
            for s in term_signals:
                sig.signal(s, quit)

            # wait for the SIGTERM from subprocess
            time.sleep(5)
        else:
            sig.signal(sig.SIGHUP, sig.SIG_IGN)
            for s in term_signals:
                sig.signal(s, self._handle_term)

            ppid = os.getppid()
            os.kill(ppid, sig.SIGTERM)
            os.setsid()

    def load_modules(self):
        self.afferent_cls = AFFERENT_MAPPING[self.role]
        self.afferent = afferent_cls(self.config)

        self.efferent = UDPTransmitter(config)

        self.protocol_wrapper = ProtocolWrapper(config)

        self.logic_handler_cls = LOGIC_HANDLER_MAPPING[self.role]
        self.logic_handler = self.logic_handler_cls(self.config)

    def handle_pkgs(self, pkgs):
        pass
        # for pkg in pkgs:
            # self.logic_handler.handle_pkg(pkg)

    def run(self):
        self.__running = True
        self.daemonize()

        self.afferent.start()
        while self.__running:
            pkgs = self.afferent.recv()
            if len(pkgs) == 0:
                continue

            self.handle_pkgs(pkgs)
