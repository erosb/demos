#!/usr/bin/python3
#coding: utf-8
import gevent
from gevent import socket

port = 12000
server_backlog = 20000
conns = 0

def handle_request(conn, addr):
    global conns
    addr = str(addr)
    try:
        with conn:
            while True:
                data = conn.recv(2048)
                if not data:
                    conn.shutdown(socket.SHUT_WR)
                    break
                # do nothing
                print('收到来自%s的数据：%s' % (addr, data.decode('utf-8')))
    except Exception as e:
        print(str(e))
        try:
            conn.shutdown(socket.SHUT_WR)
            conn.close()
        except Exception:
            pass
    finally:
        conns -= 1
        print('与%s断开连接，当前连接数%d' % (addr, conns))


def run_server():
    global conns
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('', port))
            s.listen(server_backlog)
            while True:
                conn, addr = s.accept()
                addr = str(addr)
                conns += 1
                print('与%s建立连接，当前连接数%d' % (addr, conns))
                gevent.spawn(handle_request, conn, addr)
        except KeyboardInterrupt:
            s.close()


run_server()
