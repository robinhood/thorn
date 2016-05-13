"""

    thorn.conf
    ==========

    Webhooks-related configuration settings.

"""
from __future__ import absolute_import, unicode_literals

from celery.utils import cached_property

from . import validators
from ._state import app_or_default
from .exceptions import ImproperlyConfigured
from .utils import json

__all__ = ['settings', 'event_choices']

MIME_JSON = 'application/json'
MIME_URLFORM = 'application/x-www-form-urlencoded'


class Settings(object):

    app = None

    default_chunksize = 10
    default_dispatcher = 'default'
    default_event_choices = ()
    default_timeout = 3.0
    default_codecs = {MIME_JSON: json.dumps}
    default_drf_permission_classes = None
    default_retry = True
    default_retry_max = 10
    default_retry_delay = 60.0
    default_recipient_validators = [
        validators.block_internal_ips(),
        validators.ensure_protocol('http', 'https'),
        validators.ensure_port(80, 443),
    ]

    def __init__(self, app=None):
        self.app = app_or_default(app or self.app)

    @cached_property
    def THORN_CHUNKSIZE(self):
        return (
            getattr(self.app.config, 'THORN_CHUNKSIZE', None) or
            self.default_chunksize
        )

    @cached_property
    def THORN_CODECS(self):
        return (
            getattr(self.app.config, 'THORN_CODECS', None) or
            self.default_codecs
        )

    @cached_property
    def THORN_SUBSCRIBERS(self):
        return (
            getattr(self.app.config, 'THORN_SUBSCRIBERS', None) or {}
        )

    @cached_property
    def THORN_DISPATCHER(self):
        return (
            getattr(self.app.config, 'THORN_DISPATCHER', None) or
            self.default_dispatcher
        )

    @cached_property
    def THORN_EVENT_CHOICES(self):
        return (
            getattr(self.app.config, 'THORN_EVENT_CHOICES', None) or
            self.default_event_choices
        )

    @cached_property
    def THORN_DRF_PERMISSION_CLASSES(self):
        return (
            getattr(self.app.config, 'THORN_DRF_PERMISSION_CLASSES', None) or
            self.default_drf_permission_classes
        )

    @cached_property
    def THORN_EVENT_TIMEOUT(self):
        return (
            getattr(self.app.config, 'THORN_EVENT_TIMEOUT', None) or
            self.default_timeout
        )

    @cached_property
    def THORN_RETRY(self):
        return (
            getattr(self.app.config, 'THORN_RETRY', None) or
            self.default_retry
        )

    @cached_property
    def THORN_RETRY_MAX(self):
        return (
            getattr(self.app.config, 'THORN_RETRY_MAX', None) or
            self.default_retry_max
        )

    @cached_property
    def THORN_RETRY_DELAY(self):
        return (
            getattr(self.app.config, 'THORN_RETRY_DELAY', None) or
            self.default_retry_delay,
        )

    @cached_property
    def THORN_RECIPIENT_VALIDATORS(self):
        return getattr(
            self.app.config, 'THORN_RECIPIENT_VALIDATORS',
            self.default_recipient_validators,
        )
settings = Settings()


def event_choices(app=None):
    app = app_or_default(app)
    choices = app.settings.THORN_EVENT_CHOICES
    try:
        return list(zip(choices, choices))
    except TypeError:
        raise ImproperlyConfigured('THORN_EVENT_CHOICES not a list/tuple.')


def all_settings():
    return {n for n in dir(Settings) if n.isupper() and not n.startswith('__')}
