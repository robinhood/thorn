"""Webhooks-related configuration settings."""
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
    default_signal_honors_transaction = False
    default_hmac_signer = 'thorn.utils.hmac:compat_sign'

    def __init__(self, app=None):
        self.app = app_or_default(app or self.app)

    @cached_property
    def THORN_CHUNKSIZE(self):
        return self._get('THORN_CHUNKSIZE', self.default_chunksize)

    @cached_property
    def THORN_CODECS(self):
        return self._get('THORN_CODECS', self.default_codecs)

    @cached_property
    def THORN_SUBSCRIBERS(self):
        return self._get_lazy('THORN_SUBSCRIBERS', dict)

    @cached_property
    def THORN_SUBSCRIBER_MODEL(self):
        return self._get('THORN_SUBSCRIBER_MODEL')

    @cached_property
    def THORN_HMAC_SIGNER(self):
        return self._get('THORN_HMAC_SIGNER', self.default_hmac_signer)

    @cached_property
    def THORN_DISPATCHER(self):
        return self._get('THORN_DISPATCHER', self.default_dispatcher)

    @cached_property
    def THORN_EVENT_CHOICES(self):
        return self._get('THORN_EVENT_CHOICES', self.default_event_choices)

    @cached_property
    def THORN_DRF_PERMISSION_CLASSES(self):
        return self._get(
            'THORN_DRF_PERMISSION_CLASSES',
            self.default_drf_permission_classes)

    @cached_property
    def THORN_EVENT_TIMEOUT(self):
        return self._get('THORN_EVENT_TIMEOUT', self.default_timeout)

    @cached_property
    def THORN_RETRY(self):
        return self._get('THORN_RETRY', self.default_retry)

    @cached_property
    def THORN_RETRY_MAX(self):
        return self._get('THORN_RETRY_MAX', self.default_retry_max)

    @cached_property
    def THORN_RETRY_DELAY(self):
        return self._get('THORN_RETRY_DELAY', self.default_retry_delay)

    @cached_property
    def THORN_RECIPIENT_VALIDATORS(self):
        return self._get_lazy(
            'THORN_RECIPIENT_VALIDATORS',
            lambda: list(self.default_recipient_validators))

    @cached_property
    def THORN_SIGNAL_HONORS_TRANSACTION(self):
        return self._get(
            'THORN_SIGNAL_HONORS_TRANSACTION',
            self.default_signal_honors_transaction)

    def _get(self, key, default=None):
        # type: (str, Any) -> Any
        return self._get_lazy(key, lambda: default)

    def _get_lazy(self, key, default=None):
        # type: (str, Callable[None, Any]) -> Any
        val = getattr(self.app.config, key, None)
        return val if val is not None else default()
settings = Settings()


def event_choices(app=None):
    """Return a list of valid event choices."""
    app = app_or_default(app)
    choices = app.settings.THORN_EVENT_CHOICES
    try:
        return list(zip(choices, choices))
    except TypeError:
        raise ImproperlyConfigured('THORN_EVENT_CHOICES not a list/tuple.')


def all_settings():
    return {n for n in dir(Settings) if n.isupper() and not n.startswith('__')}
