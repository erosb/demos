#!/usr/bin/python3.6
# coding: utf-8

import json
import hashlib


class ObjectifiedDict():

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return None

    @staticmethod
    def __convert(item):
        if isinstance(item, dict):
            return ObjectifiedDict(**item)
        if isinstance(item, list):
            return [ObjectifiedDict.__convert(unit) for unit in item]
        if isinstance(item, tuple):
            return (ObjectifiedDict.__convert(unit) for unit in item)
        if isinstance(item, set):
            return {ObjectifiedDict.__convert(unit) for unit in item}
        else:
            return item

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = self.__convert(value)

    def __update__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = self.__convert(value)

    def __iter__(self):
        return iter(
            self.__dict__.items()
        )

    def __bool__(self):
        return bool(self.__dict__)

    def __clear__(self):
        self.__dict__.clear()

    @staticmethod
    def __to_dumpable(item):
        if item.__class__ is bytes:
            return '<bytes length=%d>' % len(item)
        elif isinstance(item, ObjectifiedDict):
            return item.__str_assist__()
        elif item.__class__ in (list, tuple, set):
            return [ObjectifiedDict.__to_dumpable(unit) for unit in item]
        elif item.__class__ not in (int, str, None):
            return str(item)
        return item

    def __str_assist__(self):
        d = {}
        for key, value in self.__dict__.items():
            d[key] = self.__to_dumpable(value)
        return d

    def __str__(self):
        return json.dumps(
            self.__str_assist__(), indent=4
        )


class HashTools():

    @classmethod
    def _hash(cls, method, data):
        if isinstance(data, str):
            data = data.encode('utf-8')

        m = getattr(hashlib, method)()
        m.update(data)
        return m.hexdigest()

    @classmethod
    def md5(cls, data):
        return cls._hash('md5', data)

    @classmethod
    def sha1(cls, data):
        return cls._hash('sha1', data)

    @classmethod
    def sha256(cls, data):
        return cls._hash('sha256', data)

    @classmethod
    def sha512(cls, data):
        return cls._hash('sha512', data)


# from tornado.util
def errno_from_exception(e):
    """Provides the errno from an Exception object.

    There are cases that the errno attribute was not set so we pull
    the errno out of the args but if someone instatiates an Exception
    without any args you will get a tuple error. So this function
    abstracts all that behavior to give you a safe way to get the
    errno.
    """

    if hasattr(e, 'errno'):
        return e.errno
    elif e.args:
        return e.args[0]
    else:
        return None
