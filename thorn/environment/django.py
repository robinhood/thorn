"""

    thorn.environment.django
    ========================

    Django web framework environment.

"""
from __future__ import absolute_import, unicode_literals

import importlib
import os

from celery.utils import cached_property
from celery.utils.imports import symbol_by_name

__all__ = ['DjangoEnv']


class DjangoEnv(object):
    settings_cls = 'django.conf:settings'
    subscriber_cls = 'thorn.django.models:Subscriber'
    signals_cls = 'thorn.django.signals'
    reverse_cls = 'django.core.urlresolvers:reverse'

    @staticmethod
    def autodetect(env='DJANGO_SETTINGS_MODULE'):
        return os.environ.get(env)

    @cached_property
    def config(self):
        return symbol_by_name(self.settings_cls)

    @cached_property
    def Subscriber(self):
        return symbol_by_name(self.subscriber_cls)

    @cached_property
    def Subscribers(self):
        return self.Subscriber.objects

    @cached_property
    def signals(self):
        return importlib.import_module(self.signals_cls)

    @cached_property
    def reverse(self):
        return symbol_by_name(self.reverse_cls)
