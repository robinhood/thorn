"""

    thorn.dispatch.disabled
    =======================

    Dispatcher doing nothing.

"""
from __future__ import absolute_import, unicode_literals

from . import base

__all__ = ['Dispatcher']


class Dispatcher(base.Dispatcher):

    def send(self, *args, **kwargs):
        pass
