"""Internal state."""
from __future__ import absolute_import, unicode_literals

import threading

from vine.five import monotonic

__all__ = [
    'current_app', 'set_current_app', 'set_default_app',
    'app_or_default', 'buffer_events',
]


class _TLS(threading.local):
    current_app = None
_tls = _TLS()

default_app = None


def current_app():
    """Return the currently active app for this thread."""
    app = _tls.current_app
    if app is None:
        if default_app is None:
            from thorn.app import Thorn
            set_default_app(Thorn())
        return default_app
    return app


def set_current_app(app):
    """Set thread-local current app instance."""
    _tls.current_app = app


def set_default_app(app):
    """Set default app instance."""
    global default_app
    default_app = app


def app_or_default(app):
    """Return app if defined, otherwise return the default app."""
    return app if app is not None else current_app()


class buffer_events(object):
    """Context that enables event buffering.

    The buffer will be flushed at context exit, or when
    the buffer is flushed explicitly::

        with buffer_events() as buffer:
            ...
            buffer.flush()  # <-- flush here.
        # <-- # implicit flush here.
    """

    def __init__(self, flush_freq=None, flush_timeout=None, app=None):
        self.app = app_or_default(app)
        self.flush_freq = flush_freq
        self.flush_timeout = flush_timeout
        self.flush_count = 0
        self.flush_last = None

    def flush(self):
        self._flush(None)

    def maybe_flush(self):
        self.flush_count += 1
        if self.should_flush():
            self.flush()

    def should_flush(self):
        if self.flush_last is None:
            self.flush_last = monotonic()
        return (
            not self.flush_count % self.flush_freq or
            monotonic() > (self.flush_last or 0) + self.flush_timeout
        )

    def _flush(self, owner):
        self.flush_last = monotonic()
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
