#!/usr/bin/python3.6
#coding: utf-8

import json
import select
import logging

from neverland.pkt import UDPPacket, PktTypes
from neverland.utils import ObjectifiedDict
from neverland.exceptions import DropPakcet, ConfigError
from neverland.protocol.v0.subjects import ClusterControllingSubjects


logger = logging.getLogger('main')


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

    def __init__(
        self, config, efferent, logic_handler,
        protocol_wrapper, afferents=tuple(),
    ):
        ''' constructor

        :param config: the config
        :param efferent: an efferent instance
        :param logic_handler: a logic handler instance
        :param protocol_wrapper: a protocol wrapper instance
        :param afferents: a list of afferents,
                          any iterable type contains afferent instances
        '''

        self._epoll = select.epoll()
        self.afferent_mapping = {}

        self.config = config
        self.efferent = efferent
        self.logic_handler = logic_handler
        self.protocol_wrapper = protocol_wrapper

        for afferent in afferents:
            self.plug_afferent(afferent)

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
        ''' here defines how the nodes join the neverland cluster
        '''

        entrance = self.config.cluster_entrance
        identification = self.config.identification

        if entrance is None:
            raise ConfigError("cluster_entrance is not defined")
        if identification is None:
            raise ConfigError("identification is not defined")

        content = {"identification": identification}
        subject = ClusterControllingSubjects.JOIN_CLUSTER

        pkt = UDPPacket()
        ## TODO not done yet
        pkt.fields = ObjectifiedDict(
                         salt=None,
                         mac=None,
                         serial=None,
                         time=None,
                         type=PktTypes.CTRL,
                         diverged=0x01,
                         src=None,
                         dest=entrance,
                         subject=subject,
                         content=content,
                     )
        self.efferent.transmit(pkt)

    def leave_cluster(self):
        ''' here defines how the nodes detach from the neverland cluster
        '''

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
