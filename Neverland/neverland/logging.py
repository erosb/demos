#!/usr/bin/python3.6
#coding: utf-8

import sys
import logging
from logging import handlers as logging_handlers

from neverland.exceptions import ConfigError


SHM_LOGGER_NAME = 'SHM'

LOGGERS_NAMES = [
    'Main',
]


main_logger = logging.getLogger('Main')
logger = logging.getLogger('Main')


def init_all_loggers(config):
    log_level = config.log.level
    main_log_path = config.log.path_main
    shm_log_path = config.log.path_shm

    if main_log_path is None or shm_log_path is None:
        raise ConfigError('log.path_main and log.path_shm are both required')

    lv_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARN,
        'error': logging.ERROR,
    }
    lv = lv_map.get(log_level) or logging.INFO

    for logger_name in LOGGERS_NAMES:
        logger = logging.getLogger(logger_name)
        init_logger(logger, lv, main_log_path)

    logger = logging.getLogger(SHM_LOGGER_NAME)
    init_logger(logger, lv, shm_log_path)

    main_logger.info(f'Log level: {log_level}')


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
