#!/bin/sh

sudo /usr/lib/systemd/scripts/iptables-flush

sudo ip rule delete fwmark 1 table 70
sudo ip route delete local default dev lo table 70
