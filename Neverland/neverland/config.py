#!/usr/bin/python3.6
#coding: utf-8

import json

from neverland.utils import ObjectifiedDict


class ConfigLoader():

    @classmethod
    def load_json_file(cls, path):
        with open(path, 'r') as f:
            content = f.read()

        content = json.loads(content)
        config = JsonConfig(**content)
        cls.check_config(config)
        return config

    @classmethod
    def check_config(cls, config):
        pass


class JsonConfig(ObjectifiedDict):

    ''' The entity of configuration in json format
    '''
