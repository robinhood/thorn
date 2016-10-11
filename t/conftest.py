from __future__ import absolute_import, unicode_literals

import pytest

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


@pytest.fixture(autouse=True)
def test_cases_calls_setup_teardown(request):
    if request.instance:
        # we set the .patching attribute for every test class.
        setup = getattr(request.instance, 'setup', None)
        # we also call .setup() and .teardown() after every test method.
        setup and setup()
    yield
    if request.instance:
        teardown = getattr(request.instance, 'teardown', None)
        teardown and teardown()


@pytest.fixture()
def app():
    _tls, _state._tls = _state._tls, _state._TLS()
    app = Thorn(set_as_current=True)
    _default_app, _state.default_app = _state.default_app, app

    yield app

    _state.default_app = _default_app
    _state._tls = _tls


@pytest.fixture(autouse=True)
def test_cases_has_app(request, app, dispatcher, patching):
    if request.instance:
        if not hasattr(request.instance, 'app'):
            request.instance.app = app
        if not hasattr(request.instance, 'dispatcher'):
            request.instance.dispatcher = dispatcher
        if not hasattr(request.instance, 'patching'):
            request.instance.patching = patching


@pytest.fixture()
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


@pytest.fixture()
def reset_signals(request):
    wanted = getattr(request.module, "reset_signals", None)
    with _reset_signals(wanted):
        yield


@pytest.fixture()
def dispatcher():
    return Mock(name='dispatcher_set_by_fixture')


def mock_event(name, dispatcher=None, app=None, Event=Event, **kwargs):
    return Event(
        name,
        dispatcher=dispatcher,
        app=app,
        **kwargs
    )


@pytest.fixture()
def event(dispatcher, app):
    return mock_event('george.costanza', dispatcher, app)


@pytest.fixture()
def model_event(dispatcher, app):
    return mock_event('george.costanza', dispatcher, app, Event=ModelEvent)


@pytest.fixture()
def default_recipient_validators(app):
    val = app.settings.THORN_RECIPIENT_VALIDATORS = \
        app.settings.default_recipient_validators
    return val
