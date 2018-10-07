#!/usr/bin/python3.6
# coding: utf-8

import json
import hashlib


class ObjectifiedDict():

    def __getattribute__(self, name):
        container = object.__getattribute__(self, '__container__')
        if name in container:
            return container.get(name)
        else:
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                return None

    def __setattr__(self, name, value):
        self.__update__(**{name: value})

    def __convert__(self, item):
        if isinstance(item, dict):
            return ObjectifiedDict(**item)
        if isinstance(item, list):
            return [self.__convert__(unit) for unit in item]
        if isinstance(item, tuple):
            # this is necessary,
            # by default, this tuple derivation will return a generator
            return tuple(
                (self.__convert__(unit) for unit in item)
            )
        if isinstance(item, set):
            return {self.__convert__(unit) for unit in item}
        else:
            return item

    def __init__(self, **kwargs):
        object.__setattr__(self, '__container__', dict())
        for key, value in kwargs.items():
            a = self.__convert__(value)
            self.__container__[key] = a

    def __update__(self, **kwargs):
        for key, value in kwargs.items():
            self.__container__[key] = self.__convert__(value)

    def __iter__(self):
        return iter(
            self.__container__.items()
        )

    def __bool__(self):
        return bool(self.__container__)

    def __clear__(self):
        self.__container__.clear()

    @staticmethod
    def __to_dumpable__(item):
        if item.__class__ is bytes:
            return '<bytes length=%d>' % len(item)
        elif isinstance(item, ObjectifiedDict):
            return item.__str_assist__()
        elif item.__class__ in (list, tuple, set):
            return [ObjectifiedDict.__to_dumpable__(unit) for unit in item]
        elif item.__class__ not in (int, str, None):
            return str(item)

        return item

    def __str_assist__(self):
        d = {}
        for key, value in self.__container__.items():
            d[key] = self.__to_dumpable__(value)
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
