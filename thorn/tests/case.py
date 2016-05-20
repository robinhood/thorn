from __future__ import absolute_import, unicode_literals

from six import iteritems as items

from celery import Celery, current_app

from django.db.models import signals

from thorn import Thorn
from thorn.events import Event
from thorn import _state

from nose import SkipTest

from case import (
    ANY, Case, MagicMock, Mock, patch, call, mock, skip,
)

__all__ = [
    'ANY', 'Case', 'MagicMock', 'Mock', 'SkipTest',
    'patch', 'call', 'mock', 'skip',

    'EventCase', 'RealSignalCase', 'SignalCase',
]

DEFAULT_RECIPIENT_VALIDATORS = [
    ('block_internal_ips', ()),
    ('ensure_protocol', ('http://', 'https://')),
    ('ensure_port', (80, 443)),
]


def _reset_signal(sig, receivers):
    receivers, sig.receivers = sig.receivers, receivers
    try:
        sig.sender_receivers_cache.clear()
    except AttributeError:  # pragma: no cover
        pass
    return receivers


class RealSignalCase(Case):

    reset_signals = {signals.post_save, signals.post_delete}

    def setUp(self):
        self.on_setup_track_signals()
        super(RealSignalCase, self).setUp()

    def tearDown(self):
        self.on_teardown_reset_signals()
        super(RealSignalCase, self).tearDown()

    def on_setup_track_signals(self):
        self._sigstate = {
            sig: _reset_signal(sig, []) for sig in self.reset_signals
        }

    def on_teardown_reset_signals(self):
        for signal, receivers in items(self._sigstate):
            _reset_signal(signal, receivers)


class ThornCase(Case):

    def setUp(self):
        self._tls, _state._tls = _state._tls, _state._TLS()
        self.app = Thorn(set_as_current=True)
        self._default_app, _state.default_app = _state.default_app, self.app
        super(ThornCase, self).setUp()

    def tearDown(self):
        _state.default_app = self._default_app
        _state._tls = self._tls
        super(ThornCase, self).tearDown()


class SignalCase(ThornCase):

    def setUp(self):
        self.Model = Mock(name='Model')
        self.post_save = self.patch('django.db.models.signals.post_save')
        self.post_delete = self.patch('django.db.models.signals.post_delete')
        self.m2m_changed = self.patch('django.db.models.signals.m2m_changed')
        super(SignalCase, self).setUp()


class EventCase(SignalCase):
    Dispatcher = Mock
    Event = Event

    def setUp(self):
        self._prev_app = current_app._get_current_object()
        self.app = Celery(set_as_current=True)
        self.dispatcher = self.Dispatcher()
        self.event = self.mock_event('george.costanza')
        super(EventCase, self).setUp()

    def mock_event(self, name, dispatcher=None):
        return self.Event(
            name,
            dispatcher=dispatcher or self.dispatcher,
            app=self.app,
        )

    def tearDown(self):
        self._prev_app.set_current()
        super(EventCase, self).tearDown()
