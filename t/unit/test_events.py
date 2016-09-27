from __future__ import absolute_import, unicode_literals

import pickle
import pytest

from case import Mock, patch

from django.db.models.query import Q as _Q_
from django.db.transaction import TransactionManagementError

from thorn import events as _events
from thorn._state import current_app
from thorn.environment import django
from thorn.django import signals
from thorn.reverse import model_reverser
from thorn.events import Event, ModelEvent, _true
from thorn.utils.functional import Q

from conftest import mock_event


class test_Event:

    def test_init(self, event):
        assert event.name == 'george.costanza'

    def test_subscribers(self, event, dispatcher):
        subscribers = event.subscribers
        dispatcher.subscribers_for_event.assert_called_with(
            event.name, extra_subscribers=None,
        )
        assert subscribers is dispatcher.subscribers_for_event()

    def test_init__recipient_validators(self):
        x = Event('x.y', recipient_validators=[1])
        assert x.recipient_validators == [1]

    def test_subscribers__setter(self, event):
        subs = [1, 2, 3]
        event.subscribers = subs
        assert event._subscribers is subs

    def test_repr(self, event):
        assert repr(event)

    def test_send(self, event, dispatcher):
        on_success = Mock(name='on_success')
        on_timeout = Mock(name='on_timeout')
        on_error = Mock(name='on_error')
        sender = Mock(name='sender')
        event.send(
            {'foo': 'bar'}, sender=sender, timeout=3.34,
            on_success=on_success, on_timeout=on_timeout, on_error=on_error,
        )
        dispatcher.send.assert_called_with(
            event.name, {'foo': 'bar'}, sender,
            on_success=on_success, on_error=on_error,
            timeout=3.34, on_timeout=on_timeout,
            retry=None, retry_delay=None, retry_max=None,
            recipient_validators=None, headers=None,
            context=None, extra_subscribers=None, allow_keepalive=True,
        )

    def test_send__with_request_data(self, dispatcher, app):
        event = mock_event('x.y', dispatcher, app,
                           request_data={'agent': 'AGENT'})
        event.send({'foo': 'bar'})
        dispatcher.send.assert_called_with(
            event.name, {'foo': 'bar', 'agent': 'AGENT'}, None,
            on_success=None, on_error=None,
            timeout=None, on_timeout=None,
            retry=None, retry_delay=None, retry_max=None,
            recipient_validators=None, headers=None,
            context=None, extra_subscribers=None, allow_keepalive=True,
        )

    def test_send__with_disable_keepalive(self, dispatcher, app):
        event = mock_event('x.y', dispatcher, app, allow_keepalive=False)
        event.send({'foo': 'bar'})
        dispatcher.send.assert_called_with(
            event.name, {'foo': 'bar'}, None,
            on_success=None, on_error=None,
            timeout=None, on_timeout=None,
            retry=None, retry_delay=None, retry_max=None,
            recipient_validators=None, headers=None,
            context=None, extra_subscribers=None, allow_keepalive=False,
        )

    def test_dispatcher(self):
        event = Event('george.costanza', app=Mock(name='app'))
        assert event.dispatcher is event.app.dispatcher

    def test_reduce(self, event, app):
        event._dispatcher = None
        e2 = pickle.loads(pickle.dumps(event))
        assert e2.name == event.name
        assert e2.app is app


class test_ModelEvent:

    def mock_event(self, name, *args, **kwargs):
        event = self.mock_modelevent(
            name,
            reverse=model_reverser('something-view', uuid='uuid'),
            *args, **kwargs
        )
        event.reverse._reverse = Mock(name='event.reverse._reverse')
        return event

    def mock_modelevent(self, name, *args, **kwargs):
        return ModelEvent(
            name,
            *args,
            dispatcher=kwargs.pop('dispatcher', None) or self.dispatcher,
            app=kwargs.pop('app', None) or self.app,
            **kwargs
        )

    def setup(self):
        self.Model = Mock(name='Model')

    @pytest.fixture()
    def event(self):
        return self.mock_event('george.costanza')

    def test_send(self, event):
        sender = Mock(name='sender')
        event._send = Mock(name='_send')
        event.app = Mock(name='app')
        instance = Mock(name='instance')
        event.send(instance, {'foo': 'bar'}, sender=sender)
        event.app.reverse.assert_called_with(
            event.reverse.view_name,
            args=[], kwargs={'uuid': instance.uuid},
        )
        event._send.assert_called_with(
            event.name,
            {
                'event': event.name,
                'sender': sender.get_username(),
                'ref': event.app.reverse.return_value,
                'data': {'foo': 'bar'},
            },
            sender=sender,
        )

    def test_send__with_request_data(self):
        event = self.mock_event('x.y', request_data={'agent': 'AGENT'})
        event.reverse = None
        instance = Mock(name='instance')
        event.send(instance, {'foo': 'bar'}, sender=None)
        self.dispatcher.send.assert_called_with(
            event.name,
            {
                'ref': instance.get_absolute_url(),
                'data': {
                    'foo': 'bar',
                },
                'agent': 'AGENT',
                'event': 'x.y',
                'sender': None,
            },
            None,
            on_success=None, on_error=None,
            timeout=None, on_timeout=None,
            retry=None, retry_delay=None, retry_max=None,
            recipient_validators=None, headers=None,
            context=None, extra_subscribers=None, allow_keepalive=True,
        )

    def test_get_absolute_url__reverser(self):
        instance = Mock(name='instance')
        event = self.mock_modelevent('article.created')
        event.reverse = Mock(name='.reverse')
        assert event.get_absolute_url(instance) is event.reverse.return_value
        event.reverse.assert_called_once_with(instance, app=event.app)

    def test_get_absolute_url__model(self):
        instance = Mock(name='instance')
        event = self.mock_modelevent('article.created')
        event.reverse = None
        assert (
            event.get_absolute_url(instance) is
            instance.get_absolute_url.return_value
        )
        instance.get_absolute_url.assert_called_once_with()

    def test_get_absolute_url__model_but_not_defined(self):
        instance = Mock(name='instance', spec=[])
        event = self.mock_modelevent('article.created')
        event.reverse = None
        assert event.get_absolute_url(instance) is None

    def test_send__with_format_name(self):
        event = self.mock_modelevent('created.{.occasion}')
        event.reverse = None
        instance = Mock(occasion='festivus')
        event.send(instance, {'foo': 'bar'}, sender=None)
        self.dispatcher.send.assert_called_with(
            'created.festivus',
            {
                'ref': instance.get_absolute_url(),
                'data': {
                    'foo': 'bar',
                },
                'event': 'created.festivus',
                'sender': None,
            },
            None,
            on_success=None, on_error=None,
            timeout=None, on_timeout=None,
            retry=None, retry_delay=None, retry_max=None,
            recipient_validators=None, headers=None,
            context=None, extra_subscribers=None, allow_keepalive=True,
        )

    def test_dispatches_on_create(self):
        event = self.mock_event('x.on_create').dispatches_on_create()
        assert isinstance(event.signal_dispatcher, signals.dispatch_on_create)
        assert event.signal_dispatcher.fun == event.on_signal

    def test_dispatches_on_change(self):
        event = self.mock_event('x.on_change')
        event.on_signal = Mock()
        event.dispatches_on_change()
        assert isinstance(event.signal_dispatcher, signals.dispatch_on_change)
        event.signal_dispatcher.fun()
        event.on_signal.assert_called_with()
        assert event.signal_dispatcher.fun == event.on_signal

    def test_dispatches_on_delete(self):
        event = self.mock_event('x.on_change').dispatches_on_delete()
        assert isinstance(event.signal_dispatcher, signals.dispatch_on_delete)
        assert event.signal_dispatcher.fun == event.on_signal

    def test_default_filter_predicate(self):
        event = self.mock_event('foo.created')
        assert event._filter_predicate is _true

    def test_filter_predicate__filter_args(self):
        filter_fields = {'fieldA__eq': 30, 'fieldB__eq': 60}
        event = self.mock_event('foo.created', **filter_fields)
        assert isinstance(event._filter_predicate, Q)

    def test_supports_django_Q_objects(self):
        m = Mock()
        m.account.user.username = 'George'
        self.event = self.mock_modelevent('x.y', (
            _Q_(account__user__username__eq='George') |
            _Q_(account__user__username__eq='Elaine')
        ))
        assert self.event.should_dispatch(m)

        m.account.user.username = 'Jerry'
        assert not self.event.should_dispatch(m)

        m.account.user.username = 'Elaine'
        assert self.event.should_dispatch(m)

    def test_custom_signal_dispatcher(self):
        dispatcher = Mock(name='dispatcher')
        event = self.mock_event('foo.created', signal_dispatcher=dispatcher)
        dispatcher.assert_called_with(event.on_signal)
        assert event.signal_dispatcher is dispatcher()

        event.dispatches_on_create()
        event.dispatches_on_change()
        event.dispatches_on_delete()

        assert event.signal_dispatcher is dispatcher()

        event.connect_model(self.Model)
        event.signal_dispatcher.connect.assert_called_with(sender=self.Model)

    def test_connect_model__no_dispatcher(self):
        event = self.mock_event('foo.custom')
        event.connect_model(self.Model)

    def test_instance_data__defined(self, event):
        instance = self.Model()
        assert (event.instance_data(instance) is
                instance.webhooks.payload.return_value)

    def test_instance_sender__field_undefined(self, event):
        assert not event.instance_sender(self.Model())

    def test_instance_sender__field_defined(self):
        event = self.mock_event('x.y', sender_field='account.user')
        instance = self.Model()
        assert (event.instance_sender(instance) is instance.account.user)

    @patch('thorn.environment.django.on_commit')
    @patch('thorn.environment.django.partial')
    def test_on_signal__transaction(self, partial, on_commit):
        # test with signal_honor_transaction and in transaction
        event = self.mock_event('x.y', sender_field=None)
        event.signal_honors_transaction = True
        event._on_signal = Mock(name='_on_signal')
        instance = self.Model()
        event.on_signal(instance, kw=1)
        partial.assert_called_once_with(event._on_signal, instance, {'kw': 1})
        on_commit.assert_called_once_with(partial())
        event._on_signal.assert_not_called()

    @patch('thorn.environment.django.on_commit')
    @patch('thorn.environment.django.partial')
    @pytest.mark.skipif(django.on_commit is None, reason='Django <1.9')
    def test_on_signal__no_transaction(self, partial, on_commit):
        # test with signal_honor_transaction and not in transaction
        event = self.mock_event('x.y', sender_field=None)
        event.signal_honors_transaction = True
        event._on_signal = Mock(name='_on_signal')
        instance = self.Model()
        on_commit.side_effect = TransactionManagementError()
        assert django.TransactionManagementError is TransactionManagementError
        event.on_signal(instance, kw=1)
        partial.assert_called_once_with(event._on_signal, instance, {'kw': 1})
        on_commit.assert_called_once_with(partial())
        partial.return_value.assert_called_once_with()

    @patch('thorn.environment.django.on_commit')
    def test_on_signal(self, on_commit):
        instance = self.Model()
        event = self.mock_event(
            'x.y',
            sender_field='x.y.z.account',
            signal_honors_transaction=False)
        event.dispatches_on_change()
        event.send = Mock(name='ModelEvent.send')
        assert not event.signal_honors_transaction
        event.on_signal(instance)
        event.send.assert_called_with(
            instance=instance,
            data=instance.webhooks.payload.return_value,
            headers=instance.webhooks.headers.return_value,
            sender=instance.x.y.z.account,
            context={},
        )
        on_commit.assert_not_called()

    def test_on_signal__no_sender_field(self):
        instance = self.Model()
        event = self.mock_event(
            'x.y', sender_field=None, signal_honors_transaction=False)
        event.dispatches_on_change()
        event.send = Mock(name='ModelEvent.send')
        event.on_signal(instance)
        event.send.assert_called_with(
            instance=instance,
            data=instance.webhooks.payload.return_value,
            headers=instance.webhooks.headers.return_value,
            sender=None,
            context={},
        )

    def test_on_signal__raises_propagate(self):
        instance = self.Model()
        event = self.mock_event('x.y', propagate_errors=True)
        event.send_from_instance = Mock(name='send_from_instance')
        event.send_from_instance.side_effect = KeyError()
        with pytest.raises(KeyError):
            event._on_signal(instance, {'kw': 1})
        event.send_from_instance.assert_called_once_with(instance, kw=1)

    @patch('thorn.events.logger')
    def test_on_signal__raises_no_propagate(self, logger):
        instance = self.Model()
        event = self.mock_event('x.y', propagate_errors=False)
        event.send_from_instance = Mock(name='send_from_instance')
        exc = event.send_from_instance.side_effect = KeyError()
        event._on_signal(instance, {'kw': 1})
        event.send_from_instance.assert_called_once_with(instance, kw=1)
        logger.exception.assert_called_with(
            _events.E_DISPATCH_RAISED_ERROR, event.name, exc)

    def test_signal_honors_transaction__from_setting(self):
        self.app.config.THORN_SIGNAL_HONORS_TRANSACTION = True
        event = self.mock_event('x.y')
        assert event.signal_honors_transaction

    def test_signal_honors_transaction__override(self):
        self.app.config.THORN_SIGNAL_HONORS_TRANSACTION = False
        event = self.mock_event('x.y', signal_honors_transaction=True)
        assert event.signal_honors_transaction

    def test_reduce(self, event, app):
        event._kwargs['dispatcher'] = None
        event.reverse._reverse = None
        e2 = pickle.loads(pickle.dumps(event))
        assert current_app() is app
        assert e2.name == event.name
        assert e2.app is event.app
