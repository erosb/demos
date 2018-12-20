#!/usr/bin/python3.6
#coding: utf-8

import logging
from logging import handlers as logging_handlers


LOGGER_NAME_LOGPATH_MAPPING = {
    'Main': 'main_log_path',
    'SHM': 'shm_log_path',
}


logger = logging.getLogger('Main')


def init_all_loggers(log_level='info'):
    if log_path is None:
        raise ValueError('log_path is required')

    lv_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARN,
        'error': logging.ERROR,
    }
    lv = lv_map.get(log_level) or logging.INFO

    for logger_name, log_path in LOGGER_NAME_LOGPATH_MAPPING.items():
        logger = logging.getLogger(logger_name)
        init_logger(logger, lv, log_path)


def init_logger(logger, lv, log_path=None):
    logger.setLevel(lv)

    formatter = logging.Formatter(
        '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
    )

    if log_path is not None:
        fh = logging_handlers.WatchedFileHandler(log_path)
        fh.setLevel(lv)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(lv)
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    return logger
