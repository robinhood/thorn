"""Internal state."""
from __future__ import absolute_import, unicode_literals

import threading

__all__ = [
    'current_app', 'set_current_app', 'set_default_app',
    'app_or_default', 'buffer_events',
]


class _TLS(threading.local):
    current_app = None
_tls = _TLS()

default_app = None


def current_app():
    app = _tls.current_app
    if app is None:
        if default_app is None:
            from thorn.app import Thorn
            set_default_app(Thorn())
        return default_app
    return app


def set_current_app(app):
    _tls.current_app = app


def set_default_app(app):
    global default_app
    default_app = app


def app_or_default(app):
    return app if app is not None else current_app()


class buffer_events(object):

    def __init__(self, app=None):
        self.app = app_or_default(app)

    def flush(self):
        self._flush(None)

    def _flush(self, owner):
        self.app.flush_buffer(owner=owner)

    def _enable(self):
        self.app.enable_buffer(owner=self)

    def _disable(self):
        self.app.disable_buffer(owner=self)

    def __enter__(self):
        self._enable()
        return self

    def __exit__(self, *exc_inf):
        self._flush(self)
        self._disable()
