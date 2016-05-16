from __future__ import absolute_import, unicode_literals

import pickle

from django.db.models.query import Q as _Q_

from thorn.django import signals
from thorn.reverse import model_reverser
from thorn.events import Event, ModelEvent, _true
from thorn.utils.functional import Q

from .case import EventCase, Mock


class test_Event(EventCase):

    def test_init(self):
        self.assertEqual(self.event.name, 'george.costanza')

    def test_subscribers(self):
        subscribers = self.event.subscribers
        self.dispatcher.subscribers_for_event.assert_called_with(
            self.event.name,
        )
        self.assertIs(subscribers, self.dispatcher.subscribers_for_event())

    def test_repr(self):
        self.assertTrue(repr(self.event))

    def test_send(self):
        on_success = Mock(name='on_success')
        on_timeout = Mock(name='on_timeout')
        on_error = Mock(name='on_error')
        sender = Mock(name='sender')
        self.event.send(
            {'foo': 'bar'}, sender=sender, timeout=3.34,
            on_success=on_success, on_timeout=on_timeout, on_error=on_error,
        )
        self.dispatcher.send.assert_called_with(
            self.event.name, {'foo': 'bar'}, sender,
            on_success=on_success, on_error=on_error,
            timeout=3.34, on_timeout=on_timeout,
            retry=None, retry_delay=None, retry_max=None,
            recipient_validators=None,
        )

    def test_dispatcher(self):
        event = Event('george.costanza', app=Mock(name='app'))
        self.assertIs(event.dispatcher, event.app.dispatcher)

    def test_reduce(self):
        self.event._dispatcher = None
        e2 = pickle.loads(pickle.dumps(self.event))
        self.assertEqual(e2.name, self.event.name)
        self.assertIs(e2.app, self.app)


class test_ModelEvent(EventCase):

    def test_send(self):
        sender = Mock(name='sender')
        self.event._send = Mock(name='_send')
        self.event.app = Mock(name='app')
        instance = Mock(name='instance')
        self.event.send(instance, {'foo': 'bar'}, sender=sender)
        self.event.app.reverse.assert_called_with(
            self.event.reverse.view_name,
            args=[], kwargs={'uuid': instance.uuid},
        )
        self.event._send.assert_called_with(
            {
                'event': self.event.name,
                'sender': sender.get_username(),
                'ref': self.event.app.reverse.return_value,
                'data': {'foo': 'bar'},
            },
            sender=sender,
        )

    def test_dispatches_on_create(self):
        event = self.mock_event('x.on_create').dispatches_on_create()
        self.assertIsInstance(
            event.signal_dispatcher, signals.dispatch_on_create,
        )
        self.assertEqual(event.signal_dispatcher.fun, event.on_signal)

    def test_dispatches_on_change(self):
        event = self.mock_event('x.on_change')
        event.on_signal = Mock()
        event.dispatches_on_change()
        self.assertIsInstance(
            event.signal_dispatcher, signals.dispatch_on_change,
        )
        event.signal_dispatcher.fun()
        event.on_signal.assert_called_with()
        self.assertEqual(event.signal_dispatcher.fun, event.on_signal)

    def test_dispatches_on_delete(self):
        event = self.mock_event('x.on_change').dispatches_on_delete()
        self.assertIsInstance(
            event.signal_dispatcher, signals.dispatch_on_delete,
        )
        self.assertEqual(event.signal_dispatcher.fun, event.on_signal)

    def mock_event(self, name, *args, **kwargs):
        event = ModelEvent(
            name,
            dispatcher=kwargs.get('dispatcher') or self.dispatcher,
            reverse=model_reverser('something-view', uuid='uuid'),
            *args, **kwargs
        )
        event.reverse._reverse = Mock(name='event.reverse._reverse')
        return event

    def test_default_filter_predicate(self):
        event = self.mock_event('foo.created')
        self.assertIs(event._filter_predicate, _true)

    def test_filter_predicate__filter_args(self):
        filter_fields = {'fieldA__eq': 30, 'fieldB__eq': 60}
        event = self.mock_event('foo.created', **filter_fields)
        self.assertIsInstance(event._filter_predicate, Q)

    def test_supports_django_Q_objects(self):
        m = Mock()
        m.account.user.username = 'George'
        self.event = self.mock_event('x.y', (
            _Q_(account__user__username__eq='George') |
            _Q_(account__user__username__eq='Elaine')
        ))
        self.assertTrue(self.event.should_dispatch(m))

        m.account.user.username = 'Jerry'
        self.assertFalse(self.event.should_dispatch(m))

        m.account.user.username = 'Elaine'
        self.assertTrue(self.event.should_dispatch(m))

    def test_custom_signal_dispatcher(self):
        dispatcher = Mock(name='dispatcher')
        event = self.mock_event('foo.created', signal_dispatcher=dispatcher)
        dispatcher.assert_called_with(event.on_signal)
        self.assertIs(event.signal_dispatcher, dispatcher())

        event.dispatches_on_create()
        event.dispatches_on_change()
        event.dispatches_on_delete()

        self.assertIs(event.signal_dispatcher, dispatcher())

        event.connect_model(self.Model)
        event.signal_dispatcher.connect.assert_called_with(sender=self.Model)

    def test_connect_model__no_dispatcher(self):
        event = self.mock_event('foo.custom')
        event.connect_model(self.Model)

    def test_instance_data__undefined(self):
        self.assertFalse(self.event.instance_data(object()))

    def test_instance_data__defined(self):
        instance = self.Model()
        self.assertIs(
            self.event.instance_data(instance),
            instance.webhook_payload.return_value,
        )

    def test_instance_sender__field_undefined(self):
        self.assertFalse(self.event.instance_sender(self.Model()))

    def test_instance_sender__field_defined(self):
        event = self.mock_event('x.y', sender_field='account.user')
        instance = self.Model()
        self.assertIs(
            event.instance_sender(instance),
            instance.account.user,
        )

    def test_on_signal(self):
        instance = self.Model()
        event = self.mock_event('x.y', sender_field='x.y.z.account')
        event.dispatches_on_change()
        event.send = Mock(name='ModelEvent.send')
        event.on_signal(instance)
        event.send.assert_called_with(
            instance=instance,
            data=instance.webhook_payload.return_value,
            sender=instance.x.y.z.account,
        )

    def test_on_signal__no_sender_field(self):
        instance = self.Model()
        event = self.mock_event('x.y', sender_field=None)
        event.dispatches_on_change()
        event.send = Mock(name='ModelEvent.send')
        event.on_signal(instance)
        event.send.assert_called_with(
            instance=instance,
            data=instance.webhook_payload.return_value,
            sender=None,
        )

    def test_reduce(self):
        self.event._kwargs['dispatcher'] = None
        self.event.reverse._reverse = None
        print(self.event.__reduce__())
        e2 = pickle.loads(pickle.dumps(self.event))
        self.assertEqual(e2.name, self.event.name)
        self.assertIs(e2.app, self.app)
