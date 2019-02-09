#!/usr/bin/python3.6
#coding: utf-8

import os
import sys
import time
import select
import signal as sig
import logging

from neverland.exceptions import (
    FailedToJoinCluster,
    FailedToDetachFromCluster,
    SuccessfullyJoinedCluster,
)
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
from neverland.protocol.v0.subjects import ClusterControllingSubjects
from neverland.protocol.v0.fmt import (
    HeaderFormat,
    DataPktFormat,
    CtrlPktFormat,
    ConnCtrlPktFormat,
)
from neverland.components.idgeneration import IDGenerator
from neverland.components.sharedmem import SharedMemoryManager
from neverland.components.pktmngmt import (
    SpecialPacketManager,
    SpecialPacketRepeater,
)


logger = logging.getLogger('Node')


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
        self.pkt_rpter_worker_pid = None

        self.node_id = self.config.basic.node_id

    def _write_master_pid(self):
        pid_path = self.config.basic.pid_file
        pid = os.getpid()

        with open(pid_path, 'w') as f:
            f.write(str(pid))

        logger.debug(
            f'wrote pid file {pid_path} for master process, pid: {pid}'
        )

    def _handle_term_master(self, signal, sf):
        logger.debug(f'Master process received signal: {signal}')
        logger.debug(f'Start to shut down workers')
        self.shutdown_workers()

        pid_path = self.config.basic.pid_file
        if os.path.isfile(pid_path):
            logger.debug(f'Remove pid file: {pid_path}')
            os.remove(pid_path)
        sys.exit(0)

    def _handle_term_worker(self, signal, sf):
        pid = os.getpid()
        logger.debug(f'Worker {pid} received signal: {signal}')
        logger.debug(f'Shutting down worker {pid}')
        self.core.shutdown()

    def _handle_term_shm(self, signal, sf):
        pid = os.getpid()
        logger.debug(f'SharedMemoryManager {pid} received signal: {signal}')
        logger.debug(f'Shutting down SharedMemoryManager {pid}')
        self.shm_mgr.shutdown_worker()

    def _handle_term_pkt_rpter(self, signal, sf):
        pid = os.getpid()
        logger.debug(f'SpecialPacketRepeater {pid} received signal: {signal}')
        logger.debug(f'Shutting down SpecialPacketRepeater {pid}')
        self.pkt_rpter.shutdown()

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

    def _sig_pkt_rpter_worker(self):
        sig.signal(sig.SIGHUP, sig.SIG_IGN)
        for s in TERM_SIGNALS:
            sig.signal(s, self._handle_term_pkt_rpter)

    def shutdown_workers(self):
        for pid in self.worker_pids:
            self._kill(pid)

        # wait for workers to exit
        remaining = list(self.worker_pids)
        while True:
            for pid in list(remaining):
                if self._process_exists(pid):
                    os.waitpid(pid, os.WNOHANG)
                else:
                    logger.debug(f'Worker {pid} terminated')
                    remaining.remove(pid)

            if len(remaining) == 0:
                break

            time.sleep(0.5)

        # shutdown SharedMemoryManager worker at last
        self._kill(self.shm_worker_pid)
        os.waitpid(self.shm_worker_pid, 0)
        logger.debug(f'SharedMemoryManager worker {pid} terminated')
        logger.debug('All workers terminated')

    def _kill(self, pid):
        try:
            logger.debug(f'Sending SIGTERM to {pid}')
            os.kill(pid, sig.SIGTERM)
        except ProcessLookupError:
            pass

    def _process_exists(self, pid):
        try:
            os.kill(pid, 0)
        except OSError:
            logger.debug(f'Process {pid} not exists')
            return False
        else:
            logger.debug(f'Process {pid} exists')
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

        logger.debug('Node daemonized')

    def _start_shm_mgr(self):
        self.shm_mgr = SharedMemoryManager(self.config)

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
            logger.info(f'Started SharedMemoryManager: {pid}')

    def _start_pkt_rpter(self):
        self.pkt_rpter = SpecialPacketRepeater(self.config)

        pid = os.fork()
        if pid == -1:
            raise OSError('fork failed')
        elif pid == 0:
            self._sig_pkt_rpter_worker()
            self.pkt_rpter.run()
            return  # the sub-process ends here
        else:
            self.pkt_rpter_worker_pid = pid
            logger.info(f'Started SpecialPacketRepeater: {pid}')

    def _load_modules(self):
        self.afferent_cls = AFFERENT_MAPPING[self.role]
        self.main_afferent = self.afferent_cls(self.config)

        self.efferent = UDPTransmitter(self.config)

        self.protocol_wrapper = ProtocolWrapper(
                                    self.config,
                                    HeaderFormat,
                                    DataPktFormat,
                                    CtrlPktFormat,
                                    ConnCtrlPktFormat,
                                )

        self.logic_handler_cls = LOGIC_HANDLER_MAPPING[self.role]
        self.logic_handler = self.logic_handler_cls(self.config)

        self.core_cls = CORE_MAPPING.get(self.role)
        self.core = self.core_cls(
                        self.config,
                        main_afferent=self.main_afferent,
                        minor_afferents=[],
                        efferent=self.efferent,
                        logic_handler=self.logic_handler,
                        protocol_wrapper=self.protocol_wrapper,
                    )

        self.pkt_mgr = SpecialPacketManager(self.config)

        # The packet repeater is a part of the packet manager, so we will
        # use it as a normal module. Each worker shall have it's own packet
        # repeater but not share it like the shared memory manager worker
        self._start_pkt_rpter()

        logger.debug('Node modules loaded')

    def _clean_modules(self):
        self.core.shutdown()
        self.main_afferent.destroy()
        self.pkt_rpter.shutdown()

        self.main_afferent = None
        self.efferent = None
        self.protocol_wrapper = None
        self.logic_handler = None
        self.core = None
        self.pkt_mgr = None
        self.pkt_rpter = None
        self.pkt_rpter_worker_pid = None

        logger.debug('Node modules cleaned')

    def _get_modules_ready(self):
        ''' an additional init step for part of modules
        '''

        self.logic_handler.init_shm()

        self.core.self_allocate_core_id()
        self.core.init_shm()

        self.id_generator = IDGenerator(self.node_id, self.core.core_id)

        self.pkt_mgr.init_shm()

        logger.debug('Additional init step for node modules done')

    def get_context():
        return NodeContext

    def _create_context(self):
        NodeContext.pid = os.getpid()
        NodeContext.pkt_rpter_pid = self.pkt_rpter_worker_pid
        NodeContext.id_generator = self.id_generator
        NodeContext.local_ip = get_localhost_ip()
        NodeContext.core = self.core
        NodeContext.main_efferent = self.efferent
        NodeContext.protocol_wrapper = self.protocol_wrapper
        NodeContext.pkt_mgr = self.pkt_mgr

        logger.debug('Node context created')

    def _clean_context(self):
        NodeContext.pid = None
        NodeContext.pkt_rpter_pid = None
        NodeContext.id_generator = None
        NodeContext.local_ip = None
        NodeContext.core = None
        NodeContext.main_efferent = None
        NodeContext.protocol_wrapper = None

        logger.debug('Node context cleaned')

    def join_cluster(self):
        if self.role == Roles.CONTROLLER:
            raise RuntimeError(
                'Controller node is the root node of the cluster'
            )

        self.core.request_to_join_cluster()
        self.core.run_for_a_while(5)
        raise TimeoutError

    def run(self):
        self.daemonize()
        self._write_master_pid()
        self._start_shm_mgr()

        # Before we join the cluster, we need to load modules at first,
        # once we have joined the cluster, modules in the Master worker
        # shall be removed.
        self._load_modules()
        self._create_context()
        self._get_modules_ready()

        # Before we start workers, we need to join the cluster first.
        if self.role != Roles.CONTROLLER:
            try:
                self.join_cluster()
            except SuccessfullyJoinedCluster:
                logger.info('Successfully joined the cluster.')
            except FailedToJoinCluster:
                logger.error('Cannot join the cluster, request not permitted')
                return
            except TimeoutError:
                logger.error('No response from cluster, failed to join the cluster')
                return

            self._clean_modules()
            self._clean_context()

        # start normal workers
        worker_amount = self.config.basic.worker_amount
        for _ in range(worker_amount):
            pid = os.fork()

            if pid == -1:
                raise OSError('fork failed')
            elif pid == 0:
                self._sig_normal_worker()
                self._load_modules()
                self._create_context()
                self._get_modules_ready()
                self.core.run()
                return  # the sub-process ends here
            else:
                self.worker_pids.append(pid)
                logger.info(f'Started Worker: {pid}')

        os.waitpid(-1, 0)
        logger.info('Node exits.')
