#!/bin/sh

sudo iptables-restore < /etc/iptables/redir_test.rules

sudo ip rule add fwmark 1 table 70
sudo ip route add local default dev lo table 70

sudo iptables -t mangle -N UDP_REDIR_TEST
sudo iptables -t mangle -N TP_MARK

sudo iptables -t mangle -A TP_MARK -p udp -j MARK --set-mark 1

sudo iptables -t mangle -A UDP_REDIR_TEST -p udp --dport 60051 -j TPROXY --on-port 60050 --tproxy-mark 0x01/0x01

sudo iptables -t mangle -A OUTPUT -j TP_MARK
sudo iptables -t mangle -A PREROUTING -j UDP_REDIR_TEST
