from __future__ import absolute_import, unicode_literals

from django.contrib.auth import get_user_model

from thorn.django.models import Subscriber
from thorn.request import Request
from thorn.tasks import (
    send_event, dispatch_requests, dispatch_request, _worker_dispatcher,
)

from .case import (
    DEFAULT_RECIPIENT_VALIDATORS, Case, EventCase, Mock, call, patch,
)


class test_send_event(EventCase):

    @patch('thorn.tasks._worker_dispatcher')
    def test_sends_event(self, _worker_dispatcher):
        _worker_dispatcher.return_value = self.dispatcher
        send_event(self.event.name, 'foobar', 501, 3.03)
        self.dispatcher.send.assert_called_with(
            self.event.name, 'foobar', 501, timeout=3.03,
        )


class test_dispatch_requests(EventCase):

    @patch('thorn.tasks.dispatch_request')
    @patch('thorn.tasks.requests')
    def test_dispatch(self, requests, dispatch_request):
        subscriber = Subscriber(url='http://example.com')
        reqs = [
            Request(self.mock_event('foo.created'), 'a', 501, subscriber,
                    timeout=3.03),
            Request(self.mock_event('foo.changed'), 'b', 501, subscriber,
                    timeout=6.06),
            Request(self.mock_event('foo.deleted'), 'c', 501, subscriber,
                    timeout=8.08),
        ]
        dispatch_requests([req.as_dict() for req in reqs])
        requests.Session.assert_called_once_with()
        dispatch_request.assert_has_calls([
            call(session=requests.Session(), **req.as_dict()) for req in reqs
        ])


class test_dispatch_request(EventCase):

    def setUp(self):
        EventCase.setUp(self)
        self.session = Mock(name='session')
        self.user, _ = get_user_model().objects.get_or_create(
            username='test_dispatch_request',
            password='iesf&83j2aswe2',
            email='example@example.com',
        )
        self.subscriber = Subscriber(
            event='foo.created',
            url='http://example.com',
        )
        self.subscriber2 = Subscriber(
            event='foo.changed',
            url='http://example.com',
            user=self.user,
        )
        self.req = Request(
            self.subscriber.event, 'a', 501, self.subscriber, timeout=3.03)
        self.req2 = Request(
            self.subscriber2.event, 'a', 501, self.subscriber2, timeout=3.03)

    @patch('thorn.tasks.current_app')
    def test_success(self, current_app):
        _Request = current_app().Request
        dispatch_request(session=self.session, **self.req.as_dict())
        subscriber_dict = self.subscriber.as_dict()
        subscriber_dict.pop('user', None)
        current_app().Subscriber.assert_called_once_with(**subscriber_dict)
        _Request.assert_called_once_with(
            self.req.event, self.req.data,
            self.req.sender, current_app().Subscriber(),
            id=self.req.id, timeout=self.req.timeout, retry=self.req.retry,
            retry_max=self.req.retry_max, retry_delay=self.req.retry_delay,
            recipient_validators=DEFAULT_RECIPIENT_VALIDATORS,
        )
        _Request().dispatch.assert_called_once_with(
            session=self.session, propagate=_Request().retry)

    @patch('thorn.tasks.current_app')
    def test_success__with_user(self, current_app):
        _Request = current_app().Request
        dispatch_request(session=self.session, **self.req2.as_dict())
        subscriber_dict = self.subscriber2.as_dict()
        subscriber_dict.pop('user', None)
        current_app().Subscriber.assert_called_once_with(**subscriber_dict)
        _Request.assert_called_once_with(
            self.req2.event, self.req2.data,
            self.req2.sender, current_app().Subscriber(),
            id=self.req2.id, timeout=self.req2.timeout, retry=self.req2.retry,
            retry_max=self.req2.retry_max, retry_delay=self.req2.retry_delay,
            recipient_validators=DEFAULT_RECIPIENT_VALIDATORS,
        )
        _Request().dispatch.assert_called_once_with(
            session=self.session, propagate=_Request().retry)

    @patch('thorn.tasks.current_app')
    @patch('celery.app.task.Task.retry')
    def test_connection_error(self, retry, current_app):
        _Request = current_app().Request
        _Request.return_value.connection_errors = (ValueError,)
        _Request.return_value.timeout_errors = ()
        exc = _Request.return_value.dispatch.side_effect = ValueError(10)
        retry.side_effect = exc
        with self.assertRaises(ValueError):
            dispatch_request(session=self.session, **self.req.as_dict())
        retry.assert_called_with(
            exc=exc, max_retries=_Request().retry_max,
            countdown=_Request().retry_delay,
        )

    @patch('thorn.tasks.current_app')
    @patch('celery.app.task.Task.retry')
    def test_connection_error__retry_disabled(self, retry, current_app):
        _Request = current_app().Request
        _Request.return_value.connection_errors = (ValueError,)
        _Request.return_value.timeout_errors = ()
        _Request.return_value.retry = False
        exc = _Request.return_value.dispatch.side_effect = ValueError(11)
        retry.side_effect = exc
        self.req.retry = False
        with self.assertRaises(ValueError):
            dispatch_request(session=self.session, **self.req.as_dict())
        retry.assert_not_called()


class test_worker_dispatcher(Case):

    @patch('thorn.dispatch.celery.WorkerDispatcher')
    def test(self, WorkerDispatcher):
        _worker_dispatcher.clear()
        try:
            self.assertIs(_worker_dispatcher(), WorkerDispatcher())
        finally:
            _worker_dispatcher.clear()
