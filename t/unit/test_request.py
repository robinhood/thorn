from __future__ import absolute_import, unicode_literals

import pickle
import pytest

from case import Mock, skip

from thorn.conf import MIME_JSON
from thorn.exceptions import SecurityError
from thorn.request import Request

from conftest import DEFAULT_RECIPIENT_VALIDATORS


def mock_req(event, url, **kwargs):
    kwargs.setdefault('on_success', Mock(name='on_success'))
    kwargs.setdefault('on_timeout', Mock(name='on_timeout'))
    kwargs.setdefault('on_error', Mock(name='on_error'))
    subscriber = Mock(name='subscriber')
    subscriber.url = url
    subscriber.content_type = MIME_JSON
    return Request(
        event, 'data', 'george', subscriber,
        timeout=3.03,
        **kwargs
    )


@pytest.fixture()
def req(event):
    return mock_req(event.name, 'http://example.com:80/hook#id1?x=303')


@pytest.fixture()
def gethostbyname(patching):
    return patching('socket.gethostbyname',
                    return_value='123.123.123.123')


@pytest.fixture()
def logger(patching):
    return patching('thorn.request.logger')


class test_Request:

    @pytest.fixture(autouse=True)
    def setup_self(self, default_recipient_validators,
                   gethostbyname, req, event):
        self.gethostbyname = gethostbyname
        self.event = event
        self.req = req

    def test_custom_user_agent(self):
        x = mock_req('foo.bar', 'http://e.com', user_agent='MyAgent')
        assert x.user_agent == 'MyAgent'
        assert x.headers['User-Agent'] == 'MyAgent'

    def expected_headers(self, req):
        return req.annotate_headers({
            'Hook-HMAC': req.sign_request(req.subscriber, req.data),
            'Hook-Subscription': str(req.subscriber.uuid),
        })

    def test_dispatch(self):
        session = Mock(name='session')
        expected_headers = self.expected_headers(self.req)
        self.req.dispatch(session=session)
        session.post.assert_called_with(
            url=self.req.subscriber.url,
            data=self.req.data,
            headers=expected_headers,
            timeout=self.req.timeout,
        )
        self.req.on_success.assert_called_with(self.req)
        self.req.on_success = None
        self.req.dispatch(session=session)
        assert self.req.response is session.post()
        assert self.req.value is session.post()
        session.close.assert_not_called()

    def test_dispatch__cancelled(self):
        session = Mock(name='session')
        self.req.cancel()
        self.req.dispatch(session=session)
        session.post.assert_not_called()

    def test_dispatch__keepalive_disabled(self):
        self.req.allow_keepalive = False
        session = Mock(name='session')
        self.req.Session = Mock(name='req.Session')
        expected_headers = self.expected_headers(self.req)
        self.req.dispatch(session=session)
        session.post.assert_not_called()
        self.req.Session.assert_called_once_with()
        self.req.Session().post.assert_called_with(
            url=self.req.subscriber.url,
            data=self.req.data,
            headers=expected_headers,
            timeout=self.req.timeout,
        )
        self.req.Session().close.assert_called_once_with()

    def test_dispatch__connection_error(self):
        session = Mock(name='session')
        exc = session.post.side_effect = ValueError('foo')
        req = mock_req(
            self.event.name, 'http://e.com:80/hook',
            on_error=None, on_timeout=None,
        )
        req.connection_errors = (type(exc),)
        with pytest.raises(ValueError):
            req.dispatch(session=session, propagate=True)
        req.handle_connection_error = Mock(name='handle_connection_error')
        req.dispatch(session=session, propagate=False)
        req.handle_connection_error.assert_called_with(exc, propagate=False)

    def test_dispatch__illegal_port(self):
        session = Mock(name='session')
        req = mock_req(
            self.event.name, 'http://e.com:1234/hook',
        )
        with pytest.raises(SecurityError):
            req.dispatch(session=session, propagate=True)
        session.post.assert_not_called()

    def test_dispatch__timeout_error(self):
        session = Mock(name='session')
        exc = session.post.side_effect = ValueError('foo')
        req = mock_req(
            self.event.name, 'http://e.com:80/hook',
            on_error=None, on_timeout=None,
        )
        req.timeout_errors, req.connection_errors = (type(exc),), ()
        with pytest.raises(ValueError):
            req.dispatch(session=session, propagate=True)

        req.handle_timeout_error = Mock(name='handle_timeout_error')
        req.dispatch(session=session, propagate=False)
        req.handle_timeout_error.assert_called_with(exc, propagate=False)

    def test_handle_timeout_error(self, logger):
        exc = KeyError()
        self.req.handle_timeout_error(exc)
        self.req.on_timeout.fun.assert_called_with(self.req, exc)
        self.req.on_error.assert_not_called()

        self.req.on_timeout = None
        self.req.handle_timeout_error(exc)
        self.req.on_error.assert_called_with(self.req, exc)

        self.req.on_error = None
        self.req.handle_timeout_error(exc)
        logger.info.assert_called()

    def test_handle_connection_error(self, logger):
        try:
            raise KeyError()
        except KeyError as exc:
            self.req.handle_connection_error(exc)
            self.req.on_error.assert_called_with(self.req, exc)
            logger.error.assert_called()
            self.req.on_error = None
            self.req.handle_connection_error(exc)

    def test_as_dict(self):
        assert self.req.as_dict() == {
            'id': self.req.id,
            'event': self.req.event,
            'sender': self.req.sender,
            'subscriber': self.req.subscriber.as_dict(),
            'data': self.req.data,
            'timeout': self.req.timeout,
            'retry': self.req.retry,
            'retry_delay': self.req.retry_delay,
            'retry_max': self.req.retry_max,
            'recipient_validators': DEFAULT_RECIPIENT_VALIDATORS,
            'allow_keepalive': self.req.allow_keepalive,
        }

    def test_urlident(self):
        assert (mock_req('foo.bar', 'http://a.com/').urlident ==
                mock_req('foo.bar', 'http://a.com:80/bar#id1?x=y').urlident)
        assert (mock_req('foo.bar', 'http://a.com/').urlident ==
                mock_req('foo.bar', 'http://a.com').urlident)
        assert (mock_req('foo.bar', 'http://a.com:80/').urlident !=
                mock_req('foo.bar', 'http://a.com:82/').urlident)
        assert (mock_req('foo.bar', 'https://a.com/').urlident !=
                mock_req('foo.bar', 'http://a.com/').urlident)
        assert (mock_req('foo.bar', 'http://a.com/').urlident !=
                mock_req('foo.bar', 'http://b.com/').urlident)

    def test_reduce(self):

        class Subscriber(object):
            url = ''

            def as_dict(self):
                return {'value': 808}
        self.req._dispatcher = ''
        self.req.subscriber = Subscriber()
        r2 = pickle.loads(pickle.dumps(self.req))
        assert r2.app is self.app

    def test_repr(self):
        assert repr(self.req)

    @skip.if_python3()
    def test_repr__bytes_on_py2(self):
        assert isinstance(repr(self.req), bytes)
