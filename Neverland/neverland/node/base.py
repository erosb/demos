#!/usr/bin/python3.6
#coding: utf-8

import os
import sys
import time
import signal as sig
import logging

from neverland.utils import get_localhost_ip
from neverland.node import Roles
from neverland.node.context import NodeContext
from neverland.core.client import ClientCore
from neverland.core.relay import RelayCore
from neverland.core.outlet import OutletCore
from neverland.core.controller import ControllerCore
from neverland.afferents.udp import UDPReceiver, ClientUDPReceiver
from neverland.efferents.udp import UDPTransmitter
from neverland.logic.v0.client.logic_handler import ClientLogicHandler
from neverland.logic.v0.controller.logic_handler import ControllerLogicHandler
from neverland.logic.v0.outlet.logic_handler import OutletLogicHandler
from neverland.logic.v0.relay.logic_handler import RelayLogicHandler
from neverland.protocol.v0 import ProtocolWrapper
from neverland.protocol.v0.fmt import (
    HeaderFormat,
    DataPktFormat,
    CtrlPktFormat,
    ConnCtrlPktFormat,
)
from neverland.components.sharedmem import SharedMemoryManager


logger = logging.getLogger('Main')


AFFERENT_MAPPING = {
    Roles.CLIENT: ClientUDPReceiver,
    Roles.RELAY: UDPReceiver,
    Roles.OUTLET: UDPReceiver,
    Roles.CONTROLLER: UDPReceiver,
}

LOGIC_HANDLER_MAPPING = {
    Roles.CLIENT: ClientLogicHandler,
    Roles.RELAY: RelayLogicHandler,
    Roles.OUTLET: OutletLogicHandler,
    Roles.CONTROLLER: ControllerLogicHandler,
}

CORE_MAPPING = {
    Roles.CLIENT: ClientCore,
    Roles.RELAY: RelayCore,
    Roles.OUTLET: OutletCore,
    Roles.CONTROLLER: ControllerCore,
}


TERM_SIGNALS = [sig.SIGINT, sig.SIGQUIT, sig.SIGTERM]


class BaseNode():

    ''' The Base Class of Nodes
    '''

    role = None

    def __init__(self, config, role=None):
        self.config = config
        self.role = role or self.role
        self.worker_pids = []
        self.shm_worker_pid = None

    def _handle_term_master(self, signal, sf):
        self.shutdown_workers()

        pid_path = self.config.pid_file
        if os.path.isfile(pid_path):
            os.remove(pid_path)
        sys.exit(0)

    def _handle_term_worker(self, signal, sf):
        self.core.shutdown()

    def _handle_term_shm(self, signal, sf):
        self.shm_mgr.shutdown_worker()

    def _sig_master(self):
        sig.signal(sig.SIGHUP, sig.SIG_IGN)
        for s in TERM_SIGNALS:
            sig.signal(s, self._handle_term_master)

    def _sig_normal_worker(self):
        sig.signal(sig.SIGHUP, sig.SIG_IGN)
        for s in TERM_SIGNALS:
            sig.signal(s, self._handle_term_worker)

    def _sig_shm_worker(self):
        sig.signal(sig.SIGHUP, sig.SIG_IGN)
        for s in TERM_SIGNALS:
            sig.signal(s, self._handle_term_shm)

    def shutdown_workers(self):
        for pid in self.worker_pids:
            self._kill(pid)

        # wait for workers to exit
        remaining = self.worker_pids
        while True:
            for pid in list(remaining):
                if _process_exists(pid):
                    os.waitpid(pid, os.WNOHANG)
                else:
                    remaining.remove(pid)

            if len(remaining) == 0:
                break

            time.sleep(0.1)

        # shutdown SharedMemoryManager worker at last
        self._kill(self.shm_worker_pid)
        os.waitpid(self.shm_worker_pid, 0)

    def _kill(self, pid):
        try:
            os.kill(pid, sig.SIGTERM)
        except ProcessLookupError:
            pass

    def _process_exists(self, pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True

    def daemonize(self):
        pid = os.fork()
        if pid == -1: 
            raise OSError('fork failed when doing daemonize')
        elif pid > 0:
            # double fork magic
            sys.exit(0)

        pid = os.fork()
        if pid == -1: 
            raise OSError('fork failed when doing daemonize')

        def quit(sg, sf):
            sys.exit(0)

        if pid > 0:
            for s in TERM_SIGNALS:
                sig.signal(s, quit)
            time.sleep(5)
        else:
            self._sig_master()
            ppid = os.getppid()
            os.kill(ppid, sig.SIGTERM)
            os.setsid()

    def get_context():
        return NodeContext

    def _create_context(self):
        NodeContext.shm_mgr = self.shm_mgr
        NodeContext.core = self.core
        NodeContext.pid = os.getpid()
        NodeContext.local_ip = get_localhost_ip()

    def _load_modules(self):
        self.shm_mgr = SharedMemoryManager(self.config)

        self.afferent_cls = AFFERENT_MAPPING[self.role]
        self.main_afferent = afferent_cls(self.config)

        self.efferent = UDPTransmitter(config)

        self.protocol_wrapper = ProtocolWrapper(
                                    config,
                                    HeaderFormat,
                                    DataPktFormat,
                                    CtrlPktFormat,
                                    ConnCtrlPktFormat,
                                )

        self.logic_handler_cls = LOGIC_HANDLER_MAPPING[self.role]
        self.logic_handler = self.logic_handler_cls(self.config)

        self.core_cls = CORE_MAPPING.get(self.role)
        self.core = core_cls(
                        self.config,
                        main_afferent=self.main_afferent,
                        minor_afferents=[],
                        efferent=self.efferent,
                        logic_handler=self.logic_handler,
                        protocol_wrapper=self.protocol_wrapper,
                    )

    def _init_modules(self):
        ''' an additional init step for part of modules
        '''

        self.logic_handler.init_shm()

        self.core.init_shm()
        self.core.self_allocate_core_id()

    def run(self):
        self.daemonize()

        # start SharedMemoryManager worker
        pid = os.fork()
        if pid == -1:
            raise OSError('fork failed')
        elif pid == 0:
            self._sig_shm_worker()
            self.shm_mgr.run_as_worker()
            return  # the sub-process ends here
        else:
            self.shm_worker_pid = pid

        # start normal workers
        worker_amount = self.config.worker_amount
        for _ in range(worker_amount):
            pid = os.fork()

            if pid == -1:
                raise OSError('fork failed')
            elif pid == 0:
                self._sig_normal_worker()
                self._load_modules()
                self._create_context()
                self._init_modules()
                self.core.run()
                return  # the sub-process ends here
            else:
                self.worker_pids.append(pid)

        os.waitpid(-1, 0)
        logger.info('Node exits.')
