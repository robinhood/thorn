"""

    thorn.webhook.request
    =====================

    Webhook HTTP requests.

"""
from __future__ import absolute_import, unicode_literals

import thorn
import requests

from celery import uuid
from celery.utils import cached_property
from requests.exceptions import ConnectionError, Timeout
from requests.packages.urllib3.util.url import parse_url
from vine import maybe_promise, promise
from vine.abstract import Thenable, ThenableProxy

from ._state import app_or_default
from .utils.compat import restore_from_keys
from .utils.log import get_logger

__all__ = ['Request']

DEFAULT_USER_AGENT = 'Mozilla/5.0 (compatible; thorn/{0}; {1})'.format(
    thorn.__version__, requests.utils.default_user_agent(),
)

logger = get_logger(__name__)


@Thenable.register
class Request(ThenableProxy):
    """Webhook HTTP request

    :param event: Name of event.
    :param data: Event payload.
    :param sender: Sender of event (or :const:`None`).
    :param subscriber: Subscriber to dispatch the request for.

    :keyword on_success: Optional callback called if the HTTP request
        succeeds.  Must take single argument: ``request``.
    :keyword on_timeout: Optional callback called if the HTTP request
        times out. Must have signature: ``(request, exc)``.
    :keyword on_error: Optional callback called if the HTTP request
        fails.  Must have signature: ``(request, exc)``.
    :keyword headers: Additional HTTP headers to send with the request.
    :kewyord user_agent: Set custom HTTP user agent.

    :keyword retry: Retry in the event of timeout/failure?
        Disabled by default.
    :keyword retry_max: Maximum number of times to retry before giving up.
        Default is 3.
    :keyword retry_delay: Delay between retries in seconds int/float.
        Default is 60 seconds.

    """

    app = None

    Session = requests.Session

    #: Holds the response after the HTTP request is performed.
    response = None

    #: Tuple of exceptions considered a connection error.
    connection_errors = (ConnectionError,)

    #: Tuple of exceptions considered a timeout error.
    timeout_errors = (Timeout,)

    #: HTTP User-Agent header.
    user_agent = DEFAULT_USER_AGENT

    def __init__(self, event, data, sender, subscriber,
                 id=None, on_success=None, on_error=None,
                 timeout=None, on_timeout=None,
                 retry=None, retry_max=None, retry_delay=None,
                 headers=None, user_agent=None, app=None):
        self.app = app_or_default(app or self.app)
        self.id = id or uuid()
        self.event = event
        self.data = data
        self.sender = sender
        self.subscriber = subscriber
        self.timeout = timeout
        self.on_success = on_success
        self.on_timeout = maybe_promise(on_timeout)
        self.on_error = on_error
        self.retry = self.app.settings.THORN_RETRY if retry is None else retry
        self.retry_max = (
            self.app.settings.THORN_RETRY_MAX
            if retry_max is None else retry_max)
        self.retry_delay = (
            self.app.settings.THORN_RETRY_DELAY
            if retry_delay is None else retry_delay)
        self.response = None
        self._headers = headers
        self._set_promise_target(promise(
            args=(self,), callback=self.on_success, on_error=self.on_error,
        ))
        if user_agent:
            self.user_agent = user_agent

    def dispatch(self, session=None, propagate=False):
        if self.cancelled:
            return
        session = session if session is not None else self.Session()
        try:
            self.response = session.post(
                url=self.subscriber.url,
                data=self.data,
                headers=self.headers,
                timeout=self.timeout,
            )
        except self.timeout_errors as exc:
            self.handle_timeout_error(exc, propagate=propagate)
        except self.connection_errors as exc:
            self.handle_connection_error(exc, propagate=propagate)
        else:
            self._p()
        return self

    def handle_timeout_error(self, exc, propagate=False):
        logger.info('Timed out while dispatching webhook request: %r',
                    exc, exc_info=1, extra={'data': self.as_dict()})
        if self.on_timeout:
            return self.on_timeout(self, exc)
        return self._p.throw(exc, propagate=propagate)

    def handle_connection_error(self, exc, propagate=False):
        logger.error('Error dispatching webhook request: %r',
                     exc, exc_info=1, extra={'data': self.as_dict()})
        self._p.throw(exc, propagate=propagate)

    def as_dict(self):
        """Return a dictionary representation of this request
        suitable for serialization."""
        return {
            'id': self.id,
            'event': self.event,
            'sender': self.sender,
            'subscriber': self.subscriber.as_dict(),
            'data': self.data,
            'timeout': self.timeout,
            'retry': self.retry,
            'retry_max': self.retry_max,
            'retry_delay': self.retry_delay,
        }

    def __reduce__(self):
        return restore_from_keys, (type(self), (), self.__reduce_keys__())

    def __reduce_keys__(self):
        return dict(
            self.as_dict(),
            headers=self._headers,
            user_agent=self.user_agent,
        )

    @cached_property
    def headers(self):
        return dict(self.default_headers, **self._headers or {})

    @property
    def default_headers(self):
        return {
            'Content-Type': self.subscriber.content_type,
            'User-Agent': self.user_agent,
            'Hook-Event': self.event,
            'Hook-Delivery': self.id,
        }

    @cached_property
    def urlident(self):
        """Used to order HTTP requests by URL."""
        url = parse_url(self.subscriber.url)
        return url.host, url.port or 80, url.scheme or 'http'

    @property
    def value(self):
        return self.response  # here for Thenable-compatiblity.
