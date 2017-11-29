"""Django web framework environment."""
from __future__ import absolute_import, unicode_literals

import importlib
import os

from functools import partial

from celery.utils import cached_property
from celery.utils.imports import symbol_by_name

try:
    from django.db.transaction import TransactionManagementError, on_commit
except ImportError:  # pragma: no cover
    # django < 1.9
    TransactionManagementError = on_commit = None  # nqoa


__all__ = ['DjangoEnv']


class DjangoEnv(object):
    """Thorn Django environment."""

    settings_cls = 'django.conf:settings'
    subscriber_cls = 'thorn.django.models:Subscriber'
    signals_cls = 'thorn.django.signals'
    reverse_cls = 'django.core.urlresolvers:reverse'

    def on_commit(self, fun, *args, **kwargs):
        if args or kwargs:
            fun = partial(fun, *args, **kwargs)
        if on_commit is not None:
            try:
                return on_commit(fun)
            except TransactionManagementError:
                pass  # not in transaction management, execute now.
        return fun()

    @staticmethod
    def autodetect(env='DJANGO_SETTINGS_MODULE'):
        return os.environ.get(env)

    @cached_property
    def config(self):
        return symbol_by_name(self.settings_cls)

    @cached_property
    def Subscriber(self):
        return symbol_by_name(
            getattr(self.config, 'THORN_SUBSCRIBER_MODEL', None) or
            self.subscriber_cls)

    @cached_property
    def Subscribers(self):
        return self.Subscriber.objects

    @cached_property
    def signals(self):
        return importlib.import_module(self.signals_cls)

    @cached_property
    def reverse(self):
        return symbol_by_name(self.reverse_cls)
