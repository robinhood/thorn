from __future__ import absolute_import, unicode_literals

import pickle

from thorn.conf import MIME_JSON
from thorn.exceptions import SecurityError
from thorn.request import Request

from .case import DEFAULT_RECIPIENT_VALIDATORS, EventCase, Mock, patch


class test_Request(EventCase):

    def setUp(self):
        EventCase.setUp(self)
        self.req = self.mock_req(
            self.event.name, 'http://example.com:80/hook#id1?x=303',
        )
        self.gethostbyname = self.patch('socket.gethostbyname')
        self.gethostbyname.return_value = '123.123.123.123'

    def mock_req(self, event, url, **kwargs):
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

    def test_custom_user_agent(self):
        x = self.mock_req('foo.bar', 'http://e.com', user_agent='MyAgent')
        self.assertEqual(x.user_agent, 'MyAgent')
        self.assertEqual(x.headers['User-Agent'], 'MyAgent')

    def test_dispatch(self):
        session = Mock(name='session')
        self.req.dispatch(session=session)
        expected_headers = dict(self.req.headers, **{
            'Hook-HMAC': self.req.sign_request(
                self.req.subscriber, self.req.data)
        })
        session.post.assert_called_with(
            url=self.req.subscriber.url,
            data=self.req.data,
            headers=expected_headers,
            timeout=self.req.timeout,
        )
        self.req.on_success.assert_called_with(self.req)
        self.req.on_success = None
        self.req.dispatch(session=session)
        self.assertIs(self.req.response, session.post())
        self.assertIs(self.req.value, session.post())

    def test_dispatch__cancelled(self):
        session = Mock(name='session')
        self.req.cancel()
        self.req.dispatch(session=session)
        session.post.assert_not_called()

    def test_dispatch__connection_error(self):
        session = Mock(name='session')
        exc = session.post.side_effect = ValueError('foo')
        req = self.mock_req(
            self.event.name, 'http://e.com:80/hook',
            on_error=None, on_timeout=None,
        )
        req.connection_errors = (type(exc),)
        with self.assertRaises(ValueError):
            req.dispatch(session=session, propagate=True)
        req.handle_connection_error = Mock(name='handle_connection_error')
        req.dispatch(session=session, propagate=False)
        req.handle_connection_error.assert_called_with(exc, propagate=False)

    def test_dispatch__illegal_port(self):
        session = Mock(name='session')
        req = self.mock_req(
            self.event.name, 'http://e.com:1234/hook',
        )
        with self.assertRaises(SecurityError):
            req.dispatch(session=session, propagate=True)
        session.post.assert_not_called()

    def test_dispatch__timeout_error(self):
        session = Mock(name='session')
        exc = session.post.side_effect = ValueError('foo')
        req = self.mock_req(
            self.event.name, 'http://e.com:80/hook',
            on_error=None, on_timeout=None,
        )
        req.timeout_errors, req.connection_errors = (type(exc),), ()
        with self.assertRaises(ValueError):
            req.dispatch(session=session, propagate=True)

        req.handle_timeout_error = Mock(name='handle_timeout_error')
        req.dispatch(session=session, propagate=False)
        req.handle_timeout_error.assert_called_with(exc, propagate=False)

    @patch('thorn.request.logger')
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

    @patch('thorn.request.logger')
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
        self.assertDictEqual(self.req.as_dict(), {
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
        })

    def test_urlident(self):
        self.assertEqual(
            self.mock_req('foo.bar', 'http://a.com/').urlident,
            self.mock_req('foo.bar', 'http://a.com:80/bar#id1?x=y').urlident,
        )
        self.assertEqual(
            self.mock_req('foo.bar', 'http://a.com/').urlident,
            self.mock_req('foo.bar', 'http://a.com').urlident,
        )
        self.assertNotEqual(
            self.mock_req('foo.bar', 'http://a.com:80/').urlident,
            self.mock_req('foo.bar', 'http://a.com:82/').urlident,
        )
        self.assertNotEqual(
            self.mock_req('foo.bar', 'https://a.com/').urlident,
            self.mock_req('foo.bar', 'http://a.com/').urlident,
        )
        self.assertNotEqual(
            self.mock_req('foo.bar', 'http://a.com/').urlident,
            self.mock_req('foo.bar', 'http://b.com/').urlident,
        )

    def test_reduce(self):

        class Subscriber(object):
            def as_dict(self):
                return {'value': 808}
        self.req.subscriber = Subscriber()
        r2 = pickle.loads(pickle.dumps(self.req))
        self.assertIs(r2.app, self.app)
