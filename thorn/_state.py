from __future__ import absolute_import, unicode_literals

import threading


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
