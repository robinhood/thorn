from __future__ import absolute_import, unicode_literals

import pytest

from django.contrib.auth import get_user_model

from thorn.django.models import Subscriber
from thorn.request import Request
from thorn.tasks import (
    send_event, dispatch_requests, dispatch_request, _worker_dispatcher,
)

from case import Mock, call, patch

from conftest import DEFAULT_RECIPIENT_VALIDATORS, mock_event


@pytest.fixture()
def worker_dispatcher(patching, dispatcher):
    return patching('thorn.tasks._worker_dispatcher', return_value=dispatcher)


@pytest.fixture()
def mock_dispatch_request(patching):
    return patching('thorn.tasks.dispatch_request')


@pytest.fixture()
def task_retry(patching):
    return patching('celery.app.task.Task.retry')


def test_sends_event(worker_dispatcher, event):
    send_event(event.name, 'foobar', 501, 3.03, {'instance': 9})
    worker_dispatcher.return_value.send.assert_called_with(
        event.name, 'foobar', 501,
        timeout=3.03, context={'instance': 9},
    )


def test_dispatch(mock_dispatch_request, dispatcher, app):
    Session = app.Request.Session = Mock(name='Request.Session')
    subscriber = Subscriber(url='http://example.com')
    reqs = [
        Request(mock_event('foo.created', dispatcher, app),
                'a', 501, subscriber, timeout=3.03),
        Request(mock_event('foo.changed', dispatcher, app),
                'b', 501, subscriber, timeout=6.06),
        Request(mock_event('foo.deleted', dispatcher, app),
                'c', 501, subscriber, timeout=8.08),
    ]
    dispatch_requests([req.as_dict() for req in reqs])
    Session.assert_called_once_with()
    mock_dispatch_request.assert_has_calls([
        call(session=Session(), app=app, **req.as_dict())
        for req in reqs
    ])


@pytest.mark.django_db()
@pytest.mark.usefixtures('default_recipient_validators')
class test_dispatch_request:

    def setup(self):
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

    @pytest.fixture()
    def app_or_default(self, patching):
        return patching('thorn.tasks.app_or_default')

    def test_success(self, app_or_default):
        _Request = app_or_default().Request
        dispatch_request(session=self.session, **self.req.as_dict())
        subscriber_dict = self.subscriber.as_dict()
        subscriber_dict.pop('user', None)
        app_or_default().Subscriber.assert_called_once_with(**subscriber_dict)
        _Request.assert_called_once_with(
            self.req.event, self.req.data,
            self.req.sender, app_or_default().Subscriber(),
            id=self.req.id, timeout=self.req.timeout, retry=self.req.retry,
            retry_max=self.req.retry_max, retry_delay=self.req.retry_delay,
            recipient_validators=DEFAULT_RECIPIENT_VALIDATORS,
            allow_keepalive=True,
        )
        _Request().dispatch.assert_called_once_with(
            session=self.session, propagate=_Request().retry)

    def test_when_keepalive_disabled(self, app_or_default):
        _Request = app_or_default().Request
        self.req.allow_keepalive = False
        dispatch_request(session=self.session, **self.req.as_dict())
        subscriber_dict = self.subscriber.as_dict()
        subscriber_dict.pop('user', None)
        app_or_default().Subscriber.assert_called_once_with(**subscriber_dict)
        _Request.assert_called_once_with(
            self.req.event, self.req.data,
            self.req.sender, app_or_default().Subscriber(),
            id=self.req.id, timeout=self.req.timeout, retry=self.req.retry,
            retry_max=self.req.retry_max, retry_delay=self.req.retry_delay,
            recipient_validators=DEFAULT_RECIPIENT_VALIDATORS,
            allow_keepalive=False,
        )
        _Request().dispatch.assert_called_once_with(
            session=self.session, propagate=_Request().retry)

    def test_success__with_user(self, app_or_default):
        _Request = app_or_default().Request
        dispatch_request(session=self.session, **self.req2.as_dict())
        subscriber_dict = self.subscriber2.as_dict()
        subscriber_dict.pop('user', None)
        app_or_default().Subscriber.assert_called_once_with(**subscriber_dict)
        _Request.assert_called_once_with(
            self.req2.event, self.req2.data,
            self.req2.sender, app_or_default().Subscriber(),
            id=self.req2.id, timeout=self.req2.timeout, retry=self.req2.retry,
            retry_max=self.req2.retry_max, retry_delay=self.req2.retry_delay,
            recipient_validators=DEFAULT_RECIPIENT_VALIDATORS,
            allow_keepalive=True,
        )
        _Request().dispatch.assert_called_once_with(
            session=self.session, propagate=_Request().retry)

    def test_connection_error(self, task_retry, app_or_default):
        _Request = app_or_default().Request
        _Request.return_value.connection_errors = (ValueError,)
        _Request.return_value.timeout_errors = ()
        exc = _Request.return_value.dispatch.side_effect = ValueError(10)
        task_retry.side_effect = exc
        with pytest.raises(ValueError):
            dispatch_request(session=self.session, **self.req.as_dict())
        task_retry.assert_called_with(
            exc=exc, max_retries=_Request().retry_max,
            countdown=_Request().retry_delay,
        )

    def test_connection_error__retry_disabled(
            self, task_retry, app_or_default):
        _Request = app_or_default().Request
        _Request.return_value.connection_errors = (ValueError,)
        _Request.return_value.timeout_errors = ()
        _Request.return_value.retry = False
        exc = _Request.return_value.dispatch.side_effect = ValueError(11)
        task_retry.side_effect = exc
        self.req.retry = False
        with pytest.raises(ValueError):
            dispatch_request(session=self.session, **self.req.as_dict())
        task_retry.assert_not_called()


@patch('thorn.dispatch.celery.WorkerDispatcher')
def test_worker_dispatcher(self, patching):
    WorkerDispatcher = patching('thorn.dispatch.celery.WorkerDispatcher')
    _worker_dispatcher.clear()
    try:
        assert _worker_dispatcher() is WorkerDispatcher()
    finally:
        _worker_dispatcher.clear()
