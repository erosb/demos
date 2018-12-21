#!/usr/bin/python3.6
#coding: utf-8

import sys
import argparse

from neverland.exceptions import ArgumentError
from neverland.config import ConfigLoader
from neverland.node import Roles
from neverland.node.relay import RelayNode
from neverland.node.client import ClientNode
from neverland.node.outlet import OutletNode
from neverland.node.controller import ControllerNode


STANDARD_ROLE_NAME_MAPPING = {
    'client': Roles.CLIENT,
    'relay': Roles.RELAY,
    'outlet': Roles.OUTLET,
    'controller': Roles.CONTROLLER,
}

CODE_STYLE_ROLE_NAME_MAPPING = {
    '0x01': Roles.CLIENT,
    '0x02': Roles.RELAY,
    '0x03': Roles.OUTLET,
    '0x04': Roles.CONTROLLER,
}

ROLE_NODE_CLS_MAPPING = {
    Roles.CLIENT: ClientNode,
    Roles.RELAY: RelayNode,
    Roles.OUTLET: OutletNode,
    Roles.CONTROLLER: ControllerNode,
}



def parse_cli_args():
    argp = argparse.ArgumentParser(
               prog='Neverland',
               description='Construct your very own Neverland',
           )
    argp.add_argument(
        '-c',
        metavar='<path>',
        default='./nl.json',
        help='Specify the config file. default: ./nl.json',
    )
    argp.add_argument(
        '-r',
        metavar='<role>',
        help='Specify role for the node',
    )
    args = argp.parse_args()
    return args


def launch():
    args = parse_cli_args()

    config_path = args.c
    node_role_name = args.r

    node_role = (
        STANDARD_ROLE_NAME_MAPPING.get(node_role_name) or
        CODE_STYLE_ROLE_NAME_MAPPING.get(node_role_name)
    )
    if node_role is None:
        raise ArgumentError(f'Invalid role: {node_role_name}')

    node_cls = ROLE_NODE_CLS_MAPPING.get(node_role)

    config = ConfigLoader.load_json_file(config_path)

    node = node_cls(config)
    # node.run()


if __name__ == '__main__':
    launch()
