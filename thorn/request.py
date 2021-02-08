"""Webhook HTTP requests."""
from __future__ import absolute_import, unicode_literals

import thorn
import requests
import socket

from contextlib import contextmanager

from celery import uuid
from celery.utils import cached_property
from requests.exceptions import ConnectionError, Timeout
from requests.packages.urllib3.util.url import Url, parse_url
from vine import maybe_promise, promise
from vine.abstract import Thenable, ThenableProxy

from ._state import app_or_default
from .utils.compat import bytes_if_py2, restore_from_keys
from .utils.log import get_logger
from .validators import (
    block_internal_ips, deserialize_validator, serialize_validator,
)

__all__ = ['Request']

F_USER_AGENT = 'Mozilla/5.0 (compatible; thorn/{version}; {requests_UA})'

DEFAULT_USER_AGENT = F_USER_AGENT.format(
    version=thorn.__version__,
    requests_UA=requests.utils.default_user_agent(),
)

REQUEST_REPR = '<{0}: {1.event} -> {1.subscriber.url} sender={1.sender!r}>'

logger = get_logger(__name__)


@Thenable.register
class Request(ThenableProxy):
    """Webhook HTTP request.

    Arguments:
        event (str): Name of event.
        data (Any): Event payload.
        sender (Any): Sender of event (or :const:`None`).
        subscriber (~thorn.generic.models.Subscriber): Subscriber to
            dispatch the request for.

    Keyword Arguments:
        on_success (Callable): Optional callback called if
            the HTTP request succeeds.  Must take single argument: ``request``.
        on_timeout (Callable): Optional callback called if the HTTP request
            times out. Must have signature: ``(request, exc)``.
        on_error (Callable): Optional callback called if the HTTP request
            fails.  Must have signature: ``(request, exc)``.
        headers (Mapping): Additional HTTP headers to send with the request.
        user_agent (str): Set custom HTTP user agent.
        recipient_validators (Sequence): List of serialized recipient
            validators.
        allow_keepalive (bool): Allow reusing session for this HTTP request.
            Enabled by default.

        retry (bool): Retry in the event of timeout/failure?
            Disabled by default.
        retry_max (int): Maximum number of times to retry before giving up.
            Default is 3.
        retry_delay (float): Delay between retries in seconds int/float.
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
                 headers=None, user_agent=None, app=None,
                 recipient_validators=None,
                 allow_keepalive=True,
                 allow_redirects=None):
        # type: (str, Dict, Any, Subscriber, str, Callable,
        #        Callable, float, Callable, bool, int,
        #        float, Mapping, str, App, Sequence[Callable],
        #        bool, bool) -> None
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
        if recipient_validators is None:
            recipient_validators = self.app.settings.THORN_RECIPIENT_VALIDATORS
        self.allow_keepalive = allow_keepalive
        if allow_redirects is None:
            allow_redirects = self.app.settings.THORN_ALLOW_REDIRECTS
        self.allow_redirects = allow_redirects
        self._recipient_validators = recipient_validators
        self.response = None
        self._headers = headers
        self._set_promise_target(promise(
            args=(self,), callback=self.on_success, on_error=self.on_error,
        ))
        if user_agent:
            self.user_agent = user_agent

    def validate_recipient(self, url):
        # type: (str) -> None
        [validate(url) for validate in self.recipient_validators]

    def sign_request(self, subscriber, data):
        # type: (Subscriber, str) -> str
        return subscriber.sign(data)

    def dispatch(self, session=None, propagate=False):
        # type: (requests.Session, bool) -> 'Request'
        if not self.cancelled:
            self.validate_recipient(self.subscriber.url)
            with self._finalize_unless_request_error(propagate):
                self.response = self.post(session=session)
            return self

    @contextmanager
    def _finalize_unless_request_error(self, propagate=False):
        # type: (bool) -> Any
        try:
            yield
        except self.timeout_errors as exc:
            self.handle_timeout_error(exc, propagate=propagate)
        except self.connection_errors as exc:
            self.handle_connection_error(exc, propagate=propagate)
        else:
            self._p()

    @contextmanager
    def session_or_acquire(self, session=None, close_session=False):
        # type: (requests.Session, bool) -> Any
        if session is None or not self.allow_keepalive:
            session, close_session = self.Session(), True
        try:
            yield session
        finally:
            if close_session and session is not None:
                session.close()

    def to_safeurl(self, url):
        # type: (str) -> Tuple[str, str]
        # Try and see if there is any sort of redirection in the recipient URL
        # if yes, get the final URL to be passed into the validator
        if self.allow_redirects:
            try:
                _dummy_resp = requests.head(url, allow_redirects=True)
                url = _dummy_resp.url
            except ConnectionError:
                logger.warning("Recipient URL not reachable")

        parts = parse_url(url)
        host = parts.host
        addr = socket.gethostbyname(host)
        safeurl = Url(
            scheme=parts.scheme,
            auth=parts.auth,
            host=addr,
            port=parts.port,
            path=parts.path,
            query=parts.query,
            fragment=parts.fragment,
        )
        block_internal_ips()(addr)
        return host, safeurl.url

    def post(self, session=None):
        # type: (requests.Session) -> requests.Response
        host, url = self.to_safeurl(self.subscriber.url)

        with self.session_or_acquire(session) as session:
            return session.post(
                url=url,
                data=self.data,
                allow_redirects=self.allow_redirects,
                timeout=self.timeout,
                headers=self.annotate_headers({
                    'Hook-HMAC': self.sign_request(self.subscriber, self.data),
                    'Hook-Subscription': str(self.subscriber.uuid),
                    'Host': host,
                }),
                verify=False,
            )

    def handle_timeout_error(self, exc, propagate=False):
        # type: (Exception, bool) -> Any
        logger.info('Timed out while dispatching webhook request: %r',
                    exc, exc_info=1, extra={'data': self.as_dict()})
        if self.on_timeout:
            return self.on_timeout(self, exc)
        return self._p.throw(exc, propagate=propagate)

    def handle_connection_error(self, exc, propagate=False):
        # type: (Exception, bool) -> None
        logger.error('Error dispatching webhook request: %r',
                     exc, exc_info=1, extra={'data': self.as_dict()})
        self._p.throw(exc, propagate=propagate)

    def as_dict(self):
        # type: () -> Dict[str, Any]
        """Return dictionary representation of this request.

        Note:
            All values must be json serializable.
        """
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
            'recipient_validators': self._serialize_validators(
                self._recipient_validators,
            ),
            'allow_keepalive': self.allow_keepalive,
            'on_success': self.on_success,
            'on_error': self.on_error,
            'on_timeout': self.on_timeout,
        }

    def annotate_headers(self, extra_headers):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        return dict(self.headers, **extra_headers)

    def _serialize_validators(self, validators):
        # not serialized will be callable, some may have already
        # been deserialized.
        # type: (Sequence) -> Sequence
        return [serialize_validator(v)
                for v in validators if callable(v)]

    def __repr__(self):
        # type: () -> str
        return bytes_if_py2(REQUEST_REPR.format(type(self).__name__, self))

    def __reduce__(self):
        return restore_from_keys, (type(self), (), self.__reduce_keys__())

    def __reduce_keys__(self):
        # type: () -> Dict[str, Any]
        return dict(
            self.as_dict(),
            headers=self._headers,
            user_agent=self.user_agent,
        )

    @cached_property
    def headers(self):
        # type: () -> Dict[str, Any]
        return dict(self.default_headers, **self._headers or {})

    @property
    def default_headers(self):
        # type: () -> Dict[str, Any]
        return {
            'Content-Type': self.subscriber.content_type,
            'User-Agent': self.user_agent,
            'Hook-Event': self.event,
            'Hook-Delivery': self.id,
        }

    @cached_property
    def urlident(self):
        # type: () -> Tuple[str, int, str]
        """Used to order HTTP requests by URL."""
        url = parse_url(self.subscriber.url)
        return url.scheme or 'http', url.port or 80, url.host

    @property
    def value(self):
        # type: () -> Optional[requests.Response]
        return self.response  # here for Thenable-compatiblity.

    @cached_property
    def recipient_validators(self):
        # type: () -> Sequence[Callable]
        return [
            deserialize_validator(v) for v in self._recipient_validators
        ]
