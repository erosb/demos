#!/usr/bin/python3
# coding: utf-8

import errno
import logging
import select
import socket

import utils
from handler import TCPHandler
 

LOCAL_TCP_SOCKET_TIMEOUT = 3600 * 4
POLL_TIMEOUT = 4

IP_TRANSPARENT = 19
IP_RECVORIGDSTADDR = 20


class ServerMixin(object):

    # mark the server type
    _is_local = False

    # store the connection handlers, {fd: handler}
    _fd_2_handler = {}

    def __init__(self, config_path):
        self._config = self._read_config(config_path)
        self._local_sock = self._init_socket()
        self._local_sock_fd = self._local_sock.fileno()
        self._epoll = select.epoll()
        self._epoll.register(self._local_sock_fd,
                        select.EPOLLIN | select.EPOLLRDHUP | select.EPOLLERR)

    def _read_config(self, config_path):
        return utils.Initer.init_from_config_file(config_path)

    def _add_handler(self, fd, handler):
        self._fd_2_handler[fd] = handler

    def _remove_handler(self, fd):
        del self._fd_2_handler[fd]

    def run(self):
        self.__running = True
        while self.__running:
            try:
                events = self._epoll.poll(POLL_TIMEOUT)
                logging.debug('got event from epoll: %s' % str(events))
                for fd, evt in events:
                    self.handle_event(fd, evt)
            except KeyboardInterrupt:
                self.shutdown()

    def shutdown(self):
        self.__running = False


class TCPServer(ServerMixin):

    def _init_socket(self, listen_addr=None, listen_port=None, so_backlog=1024):
        listen_addr = listen_addr or self._config['listen_addr']
        listen_port = listen_port or self._config['listen_tcp_port']
        addr_info = socket.getaddrinfo(listen_addr, listen_port, 0,
                                       socket.SOCK_STREAM, socket.SOL_TCP)
        af, stype, proto, canname, sa = addr_info[0]
        sock = socket.socket(af, stype, proto)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        sock.setblocking(False)
        sock.settimeout(LOCAL_TCP_SOCKET_TIMEOUT)
        sock.bind(sa)
        sock.listen(so_backlog)
        logging.info('TCP server is listening at %s:%d' % (
                                    self._config['listen_addr'],
                                    self._config['listen_tcp_port']))
        return sock

    def handle_event(self, fd, evt):
        handler = self._fd_2_handler.get(fd)
        if fd == self._local_sock_fd and not handler:
            try:
                conn, addr = self._local_sock.accept()
                conn.settimeout(LOCAL_TCP_SOCKET_TIMEOUT)
                TCPHandler(self, conn, self._epoll, self._config,
                           self._is_local)
            except (OSError, IOError) as e:
                error_no = utils.errno_from_exception(e)
                if error_no in (errno.EAGAIN, errno.EINPROGRESS,
                                errno.EWOULDBLOCK):
                    return
        else:
            handler = self._fd_2_handler.get(fd)
            if handler:
                handler.handle_event(fd, evt)
            else:
                logging.warn('fd removed')


class UDPServer(ServerMixin):

    def _init_socket(self, listen_addr=None, listen_port=None):
        listen_addr = listen_addr or self._config['listen_addr']
        listen_port = listen_port or self._config['listen_udp_port']
        addr_info = socket.getaddrinfo(listen_addr, listen_port, 0,
                                       socket.SOCK_DGRAM)
        af, stype, proto, canname, sa = addr_info[0]
        sock = socket.socket(af, stype, proto)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if self._is_local:
            sock.setsockopt(socket.SOL_IP, IP_RECVORIGDSTADDR, 1)
            sock.setsockopt(socket.SOL_IP, IP_TRANSPARENT, 1)
        sock.setblocking(False)
        sock.bind(sa)
        return sock

    def handle_event(self, fd, evt):
        pass
