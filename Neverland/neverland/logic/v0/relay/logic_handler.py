#!/usr/bin/python3.6
#coding: utf-8

from neverland.logic.v0.base import BaseLogicHandler


class RelayLogicHandler(BaseLogicHandler):

    SHM_SOCKET_NAME_TEMPLATE = 'SHM-Logic-Relay-%d.socket'

    def __init__(self, *args, **kwargs):
        BaseLogicHandler.__init__(self, *args, **kwargs)
