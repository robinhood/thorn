from __future__ import absolute_import, unicode_literals

import pytest
import sys

from case import Mock

from contextlib import contextmanager
from six import iteritems as items

from django.db.models import signals

from thorn import Thorn, Event, ModelEvent
from thorn import _state

DEFAULT_SIGNALS = {
    signals.post_save, signals.post_delete, signals.m2m_changed,
}

DEFAULT_RECIPIENT_VALIDATORS = [
    ('block_internal_ips', ()),
    ('ensure_protocol', ('http://', 'https://')),
    ('ensure_port', (80, 443)),
]

sentinel = object()


@pytest.fixture(scope='function')
def default_recipient_validators():
    return DEFAULT_RECIPIENT_VALIDATORS


@pytest.fixture(scope='function')
def app(request):
    _tls, _state._tls = _state._tls, _state._TLS()
    app = Thorn(set_as_current=True)
    _default_app, _state.default_app = _state.default_app, app

    def fin():
        _state.default_app = _default_app
        _state._tls = _tls
    request.addfinalizer(fin)
    return app


@pytest.fixture(scope='function')
def signals(patching):
    signals = Mock(name='signals')
    patching('django.db.models.signals.post_save', signals.post_save)
    patching('django.db.models.signals.post_delete', signals.post_delete)
    patching('django.db.models.signals.m2m_changed', signals.m2m_changed)
    return signals


def _reset_signal(sig, receivers):
    receivers, sig.receivers = sig.receivers, receivers
    try:
        sig.sender_receivers_cache.clear()
    except AttributeError:
        pass
    return receivers


@contextmanager
def _reset_signals(wanted=None):
    _sigstate = {
        sig: _reset_signal(sig, []) for sig in wanted or DEFAULT_SIGNALS
    }
    try:
        yield
    finally:
        for signal, receivers in items(_sigstate):
            _reset_signal(signal, receivers)


@pytest.fixture(scope='function')
def reset_signals(request):
    wanted = getattr(request.module, "reset_signals", None)
    ctx = _reset_signals(wanted)
    ctx.__enter__()
    request.addfinalizer(lambda: ctx.__exit__(*sys.exc_info()))


@pytest.fixture(scope='function')
def dispatcher():
    return Mock(name='dispatcher')


def mock_event(name, dispatcher=None, app=None, Event=Event, **kwargs):
    return Event(
        name,
        dispatcher=dispatcher,
        app=app,
        **kwargs
    )


@pytest.fixture(scope='function')
def event(dispatcher, app):
    return mock_event('george.costanza', dispatcher, app)


@pytest.fixture(scope='function')
def model_event(dispatcher, app):
    return mock_event('george.costanza', dispatcher, app, Event=ModelEvent)
