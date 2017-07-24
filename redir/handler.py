# coding: utf-8

import errno
import select
import socket
import struct
import logging

import utils


REMOTE_TCP_SOCKET_TIMEOUT = 3600 * 4

SO_ADDR_SIZE = 16
SO_ORIGINAL_DST = 80

UP_STREAM_BUF_SIZE = 16384
DOWN_STREAM_BUF_SIZE = 32768

# mechanism of status, from shadowsocks.tcprelay
STREAM_UP = 0
STREAM_DOWN = 1
WAIT_STATUS_INIT = 0
WAIT_STATUS_READING = 1
WAIT_STATUS_WRITING = 2
WAIT_STATUS_READWRITING = WAIT_STATUS_READING | WAIT_STATUS_WRITING


class TCPHandler():

    def __init__(self, server, local_conn, epoll, config, is_local):
        self._server = server
        self._local_conn = local_conn
        self._remote_conn = None
        self._epoll = epoll
        self._config = config
        self._is_local = is_local
        self._upstream_status = WAIT_STATUS_READING
        self._downstream_status = WAIT_STATUS_INIT
        self._add_conn_to_poll(self._local_conn,
                       select.EPOLLIN | select.EPOLLRDHUP | select.EPOLLERR)
        self._data_2_local_sock = []
        self._data_2_remote_sock = []
        self._destroyed = False
        logging.debug('Created local socket, fd: %d' % self._local_conn.fileno())

    def _fd_2_conn(self, fd):
        if fd == self._local_conn.fileno():
            return self._local_conn
        if self._remote_conn and self._remote_conn.fileno() == fd:
            return self._remote_conn
        return None

    def _add_conn_to_poll(self, conn, mode):
        self._epoll.register(conn.fileno(), mode)
        self._server._add_handler(conn.fileno(), self)

    def _get_sock_opt(self, conn):
        opt = conn.getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, SO_ADDR_SIZE)
        return utils.unpack_sockopt(opt)

    def _local_get_dest_info(self):
        opt = self._get_sock_opt(self._local_conn)
        return opt[1:]

    def _local_format_dest_info(self, dest_info):
        port = struct.pack('H', dest_info[0])
        ip = b''.join([struct.pack('B', u) for u in dest_info[1:]])
        return ip + port

    def __unpack(self, mode, b):
        return struct.unpack(mode, b)[0]

    def _remote_unpack_data(self, data):
        # tmp
        # 临时测试用
        dest = data[:6]
        dest_ip = '%d.%d.%d.%d' % (dest[0], dest[1], dest[2], dest[3])
        dest_port = self.__unpack('H', dest[4:6])
        return (dest_ip, dest_port), data[6:]


    def _create_remote_conn(self, ip, port):
        addrs = socket.getaddrinfo(ip, port, 0, socket.SOCK_STREAM,
                                   socket.SOL_TCP)
        if len(addrs) == 0:
            logging.error("getaddrinfo failed for %s:%d" % (ip, port))
            return None
        af, socktype, proto, canonname, sa = addrs[0]
        remote_sock = socket.socket(af, socktype, proto)
        remote_sock.setblocking(False)
        remote_sock.settimeout(REMOTE_TCP_SOCKET_TIMEOUT)
        remote_sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        logging.info('created remote socket, %s:%d, fd: %d' %\
                        (ip, port, remote_sock.fileno()))
        return remote_sock

    def _write_to_sock(self, data, conn):
        # from shadowsocks.tcprelay.TCPRelayHandler._write_to_sock
        # I made some change to fit my project.

        if not data or not conn:
            return False
        uncomplete = False
        try:
            l = len(data)
            s = conn.send(data)
            if s < l:
                data = data[s:]
                uncomplete = True
        except (OSError, IOError) as e:
            if utils.errno_from_exception(e) in (errno.EAGAIN, errno.EINPROGRESS,
                                                 errno.EWOULDBLOCK):
                uncomplete = True
            else:
                self.destroy()
                return False
        if uncomplete:
            if conn == self._local_conn:
                logging.debug('write to local uncompleted,\
                                %dB sent, %dB stored' % (s, l - s))
                self._data_2_local_sock.append(data)
                self._update_stream(STREAM_DOWN, WAIT_STATUS_WRITING)
            elif conn == self._remote_conn:
                logging.debug('write to %s:%d uncompleted,\
                                %dB sent, %dB stored' %\
                                (self._remote_ip, self._remote_port, s, l - s))
                self._data_2_remote_sock.append(data)
                self._update_stream(STREAM_UP, WAIT_STATUS_WRITING)
            else:
                logging.error('write_all_to_sock:unknown socket')
        else:
            if conn == self._local_conn:
                logging.debug('wrote %dB to local socket' % l)
                self._update_stream(STREAM_DOWN, WAIT_STATUS_READING)
            elif conn == self._remote_conn:
                logging.debug('wrote %dB to remote socket @ %s:%d' %\
                                (l, self._remote_ip, self._remote_port))
                self._update_stream(STREAM_UP, WAIT_STATUS_READING)
            else:
                logging.error('write_all_to_sock:unknown socket')
        return True

    def _update_stream(self, stream, status):
        # from shadowsocks.tcprelay.TCPRelayHandler._update_stream
        # I made some change to fit my project.

        dirty = False
        if stream == STREAM_DOWN:
            if self._downstream_status != status:
                self._downstream_status = status
                dirty = True
        elif stream == STREAM_UP:
            if self._upstream_status != status:
                self._upstream_status = status
                dirty = True
        if not dirty:
            return

        if self._local_conn:
            event = select.EPOLLRDHUP | select.EPOLLERR
            if self._downstream_status & WAIT_STATUS_WRITING:
                event |= select.EPOLLOUT
            if self._upstream_status & WAIT_STATUS_READING:
                event |= select.EPOLLIN
            self._epoll.modify(self._local_conn.fileno(), event)
        if self._remote_conn:
            event = select.EPOLLRDHUP | select.EPOLLERR
            if self._downstream_status & WAIT_STATUS_READING:
                event |= select.EPOLLIN
            if self._upstream_status & WAIT_STATUS_WRITING:
                event |= select.EPOLLOUT
            self._epoll.modify(self._remote_conn.fileno(), event)

    def _on_local_read(self):
        # from shadowsocks.tcprelay.TCPRelayHandler._on_local_read
        # I made some change to fit my project.

        if self._destroyed:
            return

        if self._is_local:
            buf_size = UP_STREAM_BUF_SIZE
        else:
            buf_size = DOWN_STREAM_BUF_SIZE
        try:
            data = self._local_conn.recv(buf_size)
        except (OSError, IOError):
            if utils.errno_from_exception(e) in (errno.ETIMEDOUT, errno.EAGAIN,
                                                 errno.EWOULDBLOCK):
                return
        if not data:
            self.destroy()
            return

        if self._is_local:
            remote_ip = self._config.get('server_addr')
            remote_port = self._config.get('server_tcp_port')
            dest_info = self._local_get_dest_info()
            header = self._local_format_dest_info(dest_info)
            # tmp
            # 临时性测试用，将4+2字节的目标ipv4信息附于头部
            data = header + data
        else:
            remote_info, data = self._remote_unpack_data(data)
            remote_ip = remote_info[0]
            remote_port = remote_info[1]
        self._remote_ip = remote_ip
        self._remote_port = remote_port
        self._data_2_remote_sock.append(data)
        logging.debug('%dB to %s:%d, stored' %\
                        (len(data), remote_ip, remote_port))

        if not self._remote_conn:
            if self._is_local:
                if not (remote_ip and remote_port):
                    raise ValueError(
                            "can't find config server_addr/server_tcp_port")
            else:
                if not (remote_ip and remote_port):
                    logging.warn("can't find dest info from data")
                    self.destroy()
                    return
            self._remote_conn = self._create_remote_conn(remote_ip, remote_port)
            try:
                self._remote_conn.connect((remote_ip, remote_port))
            except (OSError, IOError) as e:
                if utils.errno_from_exception(e) == errno.EINPROGRESS:
                    pass
            self._add_conn_to_poll(self._remote_conn,
                       select.EPOLLOUT | select.EPOLLRDHUP | select.EPOLLERR)
            self._update_stream(STREAM_UP, WAIT_STATUS_READWRITING)
            self._update_stream(STREAM_DOWN, WAIT_STATUS_READING)
        else:
            self._on_remote_write()

    def _on_remote_write(self):
        # from shadowsocks.tcprelay.TCPRelayHandler._on_remote_write
        # I made some change to fit my project.

        if self._destroyed:
            return

        if self._data_2_remote_sock:
            data = b''.join(self._data_2_remote_sock)
            self._data_2_remote_sock = []
            self._write_to_sock(data, self._remote_conn)
        else:
            self._update_stream(STREAM_UP, WAIT_STATUS_READING)

    def _on_remote_read(self):
        # from shadowsocks.tcprelay.TCPRelayHandler._on_remote_read
        # I made some change to fit my project.

        if self._destroyed:
            return

        if self._is_local:
            buf_size = UP_STREAM_BUF_SIZE
        else:
            buf_size = DOWN_STREAM_BUF_SIZE
        try:
            data = self._remote_conn.recv(buf_size)
        except (OSError, IOError):
            if utils.errno_from_exception(e) in (errno.ETIMEDOUT, errno.EAGAIN,
                                                 errno.EWOULDBLOCK):
                return
        if not data:
            self.destroy()
            return
        try:
            self._write_to_sock(data, self._local_conn)
        except Exception:
            self.destroy()

    def _on_local_write(self):
        # from shadowsocks.tcprelay.TCPRelayHandler._on_local_write
        # I made some change to fit my project.

        if self._destroyed:
            return

        if self._data_2_local_sock:
            data = b''.join(self._data_2_local_sock)
            self._data_2_local_sock = []
            self._write_to_sock(data, self._local_conn)
        else:
            self._update_stream(STREAM_DOWN, WAIT_STATUS_READING)

    def _on_local_disconnect(self):
        logging.debug('local socket got EPOLLRDHUP, do destroy()')
        self.destroy()

    def _on_remote_disconnect(self):
        logging.debug('remote socket got EPOLLRDHUP, do destroy()')
        self.destroy()

    def _on_local_error(self):
        logging.warn('local socket got EPOLLERR, do destroy()')
        self.destroy()

    def _on_remote_error(self):
        logging.warn('remote socket got EPOLLERR, do destroy()')
        self.destroy()

    def handle_event(self, fd, evt):
        logging.debug('handle event: %d, fd: %d' % (evt, fd))
        if self._destroyed:
            logging.info('handler destroyed')
            return
        conn = self._fd_2_conn(fd)
        if not conn:
            logging.warn('unknow socket error, do destroy()')
            return

        if conn == self._remote_conn:
            if evt & select.EPOLLRDHUP:
                self._on_remote_disconnect()
            if evt & select.EPOLLERR:
                self._on_remote_error()
            if evt & (select.EPOLLIN | select.EPOLLHUP):
                self._on_remote_read()
            if evt & select.EPOLLOUT:
                self._on_remote_write()
        elif conn == self._local_conn:
            if evt & select.EPOLLRDHUP:
                self._on_local_disconnect()
            if evt & select.EPOLLERR:
                self._on_local_error()
            if evt & (select.EPOLLIN | select.EPOLLHUP):
                self._on_local_read()
            if evt & select.EPOLLOUT:
                self._on_local_write()

    def destroy(self):
        if self._destroyed:
            logging.debug('handler already destroyed')
            return

        self._destroyed = True
        loc_fd = self._local_conn.fileno()
        self._server._remove_handler(loc_fd)
        self._epoll.unregister(loc_fd)
        self._local_conn.close()
        self._local_conn = None
        logging.debug('local socket destroyed, fd: %d' % loc_fd)
        if self._remote_conn:
            rmt_fd = self._remote_conn.fileno()
            self._server._remove_handler(rmt_fd)
            self._epoll.unregister(rmt_fd)
            self._remote_conn.close()
            self._remote_conn = None
            logging.debug('remote socket destroyed, fd: %d' % rmt_fd)


class UDPHandler():
    ''' UDP doesn't need a handler.
        I just need to relay the packets without thinking.
    '''
