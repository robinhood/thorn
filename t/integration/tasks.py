"""Tasks used for functional testing.

Custom Celery worker remote control commands
used in the Thorn functional test suite.
"""
from __future__ import absolute_import, unicode_literals
from collections import Mapping
from six import text_type
from celery.worker.control import control_command, ok
from kombu.utils.imports import symbol_by_name
from thorn._state import current_app


@control_command(
    args=[('setting_name', text_type), ('new_value', None)],
    signature='<setting_name> <new_value>',
)
def setenv(state, setting_name, new_value):
    """Remote control command to set Thorn application setting."""
    app = current_app()
    value = getattr(app.settings, setting_name, None)
    setattr(app.settings, setting_name, new_value)
    return ok(value)


def subscribers_for_event(event):
    """Get a list of subscribers for an even by name."""
    app = current_app()
    subs = app.settings.THORN_SUBSCRIBERS.get(event)
    if subs is None:
        subs = app.settings.THORN_SUBSCRIBERS[event] = []
    elif not isinstance(subs, list):
        subs = app.settings.THORN_SUBSCRIBERS[event] = [subs]
    return subs


def find_subscriber(self, subs, url):
    """Find specific subscriber by URL."""
    for i, sub in enumerate(subs):
        if sub == url or (isinstance(sub, Mapping) and sub['url'] == url):
            return i


def _unsubscribe(subs, url):
    try:
        subs.pop(find_subscriber(subs, url))
    except TypeError:
        pass


@control_command(
    args=[
        ('event', text_type),
        ('url', text_type),
        ('callback', text_type),
    ],
    signature='<event_name> [url, [callback_path]]',
)
def hook_subscribe(state, event, url=None, callback=None):
    """Subscribe to webhook."""
    subs = subscribers_for_event(event)
    _unsubscribe(subs, url)
    subscribers_for_event(event).append(
        symbol_by_name(callback) if callback else url,
    )
    return ok('url {0!r} subscribed to event {1!r}'.format(url, event))


@control_command(
    args=[('event', text_type), ('url', text_type)],
    signature='<event_name> <url>',
)
def hook_unsubscribe(state, event, url):
    """Unsubscribe from webhook."""
    _unsubscribe(subscribers_for_event(event), url)
    return ok('url {0!r} unsubscribed from event {1!r}'.format(url, event))


@control_command(
    args=[('event', text_type)],
    signature='<event_name>',
)
def hook_clear(state, event):
    """Clear recorded hooks."""
    subscribers_for_event(event)[:] = []
    return ok('removed all subscribers for event {0!r}'.format(event))
