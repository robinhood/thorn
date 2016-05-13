"""

    thorn.utils.log
    ===============

    Logging utilities.

"""
from __future__ import absolute_import, unicode_literals

from six import string_types

from kombu.log import get_logger as _get_logger

__all__ = ['base_logger', 'get_logger']

base_logger = _get_logger('webhooks')


def get_logger(name, parent=base_logger):
    assert isinstance(name, string_types)
    logger = _get_logger(name)
    logger.parent = parent
    return logger
