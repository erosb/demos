#!/usr/bin/python3.6
#coding: utf-8

import os
import json
import select
import logging

from neverland.pkt import UDPPacket, PktTypes
from neverland.node.context import NodeContext
from neverland.utils import ObjectifiedDict, get_localhost_ip
from neverland.exceptions import DropPakcet, ConfigError
from neverland.protocol.v0.subjects import ClusterControllingSubjects
from neverland.core.status import ClusterControllingStatus
from neverland.components.sharedmem import (
    SHMContainerTypes,
    SharedMemoryManager,
)


POLL_TIMEOUT = 4

logger = logging.getLogger('Main')


class BaseCore():

    ''' The base model of cores

    Literally, the core is supposed to be a kernel-like component.
    It organizes other components to work together and administrate them.
    Some components are plugable, and some others are necessary.

    Here is the list of all plugable components:
        afferents in neverland.afferents, plugable
        efferents in neverland.efferents, necessary
        logic handlers in neverland.logic, necessary
        protocol wrappers in neverland.protocol, necessary

    In the initial version, all these components are necessary, and afferents
    could be multiple.
    '''

    EV_MASK = select.EPOLLIN

    SHM_SOCKET_NAME_TEMPLATE = 'SHM-Core-%d.socket'

    # SHM container for containing allocated core id
    # data structure:
    #     [1, 2, 3, 4]
    SHM_KEY_CORE_ID = 'Core_id'

    # The shared status of cluster controlling,
    # enumerated in neverland.core.status.ClusterCtrlStatus
    SHM_KEY_CTRL_STATUS = 'Core_CtrlStatus'

    def __init__(
        self, config, efferent, logic_handler,
        protocol_wrapper, main_afferent, minor_afferents=tuple(),
    ):
        ''' constructor

        :param config: the config
        :param efferent: an efferent instance
        :param logic_handler: a logic handler instance
        :param protocol_wrapper: a protocol wrapper instance
        :param main_afferent: the main afferent
        :param minor_afferents: a group of minor afferents,
                                any iterable type contains afferent instances
        '''

        self.core_id = None
        self._epoll = select.epoll()
        self.afferent_mapping = {}

        self.config = config
        self.main_afferent = main_afferent
        self.efferent = efferent
        self.logic_handler = logic_handler
        self.protocol_wrapper = protocol_wrapper

        self.shm_mgr = SharedMemoryManager(self.config)

        self.plug_afferent(self.main_afferent)

        for afferent in minor_afferents:
            self.plug_afferent(afferent)

    def _set_ctrl_status(self, status):
        self.shm_mgr.set_value(self.SHM_KEY_CTRL_STATUS, status)

    def _get_ctrl_status(self):
        resp = self.shm_mgr.read_key(self.SHM_KEY_CTRL_STATUS)
        return resp.get('value')

    def init_shm(self):
        self.shm_mgr.connect(
            self.SHM_SOCKET_NAME_TEMPLATE % NodeContext.pid
        )
        self.shm_mgr.create_key(
            self.SHM_KEY_CORE_ID,
            SHMContainerTypes.LIST,
        )
        self.shm_mgr.create_key(
            self.SHM_KEY_CTRL_STATUS,
            SHMContainerTypes.INT,
            ClusterControllingStatus.INIT,
        )

        logger.debug(f'init_shm for core of worker {NodeContext.pid} has done')

    def self_allocate_core_id(self):
        ''' Let the core pick up an id for itself
        '''

        resp = self.shm_mgr.read_key(self.SHM_KEY_CORE_ID)
        allocated_id = resp.get('value')

        if len(allocated_id) == 0:
            id_ = 0
        else:
            last_id = allocated_id[-1]
            id_ = last_id + 1

        self.shm_mgr.add_value(
            self.SHM_KEY_CORE_ID,
            [id_],
        )
        self.core_id = id_

        logger.debug(
            f'core of worker {NodeContext.pid} has self-allocated id: {id_}'
        )

    def plug_afferent(self, afferent):
        self._epoll.register(afferent.fd, self.EV_MASK)
        self.afferent_mapping.update(
            {afferent.fd: afferent}
        )

    def unplug_afferent(self, fd):
        ''' remove an afferent from the core

        :param fd: the file discriptor of the afferent, int
        '''

        if fd not in self.afferent_mapping:
            return

        self._epoll.unregister(fd)
        self.afferent_mapping.pop(fd)

    def join_cluster(self):
        ''' here defines how the node join the neverland cluster
        '''

        entrance = self.config.cluster_entrance
        identification = self.config.net.identification

        if entrance is None:
            raise ConfigError("cluster_entrance is not defined")
        if identification is None:
            raise ConfigError("identification is not defined")

        logger.info('Trying to join cluster...')

        local_ip = get_localhost_ip()
        port = self.main_afferent.listen_port
        src = (local_ip, port)

        content = {"identification": identification}
        subject = ClusterControllingSubjects.JOIN_CLUSTER

        pkt = UDPPacket()
        pkt.fields = ObjectifiedDict(
                         type=PktTypes.CTRL,
                         src=src,
                         dest=entrance,
                         subject=subject,
                         content=content,
                     )
        pkt.next_hop = entrance

        pkt = self.protocol_wrapper.wrap(pkt)
        self.efferent.transmit(pkt)

        logger.info(
            f'Sent request to cluster entrance {entrance.ip}:{entrance.port}'
        )

        logger.info('[Node Status] WAITING_FOR_JOIN')
        self._set_ctrl_status(ClusterControllingStatus.WAITING_FOR_JOIN)

    def leave_cluster(self):
        ''' here defines how the node detach from the neverland cluster
        '''

        entrance = self.config.cluster_entrance
        identification = self.config.net.identification

        if entrance is None:
            raise ConfigError("cluster_entrance is not defined")
        if identification is None:
            raise ConfigError("identification is not defined")

        logger.info('Trying to leave cluster...')

        local_ip = get_localhost_ip()
        port = self.main_afferent.listen_port
        src = (local_ip, port)

        content = {"identification": identification}
        subject = ClusterControllingSubjects.LEAVE_CLUSTER

        pkt = UDPPacket()
        pkt.fields = ObjectifiedDict(
                         type=PktTypes.CTRL,
                         src=src,
                         dest=entrance,
                         subject=subject,
                         content=content,
                     )
        pkt.next_hop = entrance

        pkt = self.protocol_wrapper.wrap(pkt)
        self.efferent.transmit(pkt)

        logger.info(
            f'Sent request to cluster entrance {entrance.ip}:{entrance.port}'
        )

        logger.info('[Node Status] WAITING_FOR_LEAVE')
        self._set_ctrl_status(ClusterControllingStatus.WAITING_FOR_LEAVE)

    def handle_pkt(self, pkt):
        pkt = self.protocol_wrapper.unwrap(pkt)

        if not pkt.valid:
            return

        try:
            pkt = self.logic_handler.handle_logic(pkt)
        except DropPakcet:
            return

        pkt = self.protocol_wrapper.wrap(pkt)
        self.efferent.transmit(pkt)

    def run(self):
        self.__running = True
        while self.__running:
            events = self._epoll.poll(POLL_TIMEOUT)
            for fd, evt in events:
                afferent = self.afferent_mapping[fd]

                if evt & select.EPOLLERR:
                    self.unplug_afferent(fd)
                    afferent.distory()
                elif evt & select.EPOLLIN:
                    pkt = afferent.recv()
                    self.handle_pkt(pkt)

    def shutdown(self):
        self.__running = False
