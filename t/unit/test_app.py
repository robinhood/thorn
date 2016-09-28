from __future__ import absolute_import, unicode_literals

import pickle
import pytest
import thorn.dispatch.disabled
import thorn.dispatch.base

from case import Mock

from thorn import Thorn
from thorn.decorators import webhook_model
from thorn.events import Event, ModelEvent
from thorn.reverse import model_reverser
from thorn.request import Request


class Subscriber(object):

    def as_dict(self):
        return {}


def test_set_default(app, patching):
    set_default_app = patching('thorn._state.set_default_app')
    app.set_default()
    set_default_app.assert_called_once_with(app)


class test_dispatcher:

    def test_argument(self):

        class Dispatcher(object):
            app = None

        app = Thorn(set_as_current=False, dispatcher=Dispatcher)
        assert isinstance(app.dispatcher, Dispatcher)
        assert app.dispatcher.app is app

    def test_setting(self, app):
        app.settings.THORN_DISPATCHER = 'disabled'
        assert isinstance(app.dispatcher, thorn.dispatch.disabled.Dispatcher)
        assert app.dispatcher.app is app

    def test_default(self, app):
        assert isinstance(app.dispatcher, thorn.dispatch.base.Dispatcher)

    def test_pickle(self, app):
        assert pickle.loads(pickle.dumps(app.dispatcher)).app is app


def test_Subscriber(app):
    app.env = Mock(name='env')
    assert app.Subscriber is app.env.Subscriber


def test_Subscribers(app):
    app.env = Mock(name='env')
    assert app.Subscribers is app.env.Subscribers


def test_signals(app):
    app.env = Mock(name='env')
    assert app.signals is app.env.signals


def test_reverse(app):
    app.env = Mock(name='env')
    assert app.reverse is app.env.reverse


@pytest.mark.parametrize('attr_name,cls', [
    ('Event', Event),
    ('ModelEvent', ModelEvent),
])
def test_Event(attr_name, cls, app):
    attr = getattr(app, attr_name)
    event = attr('article.created')
    assert event.app is app
    assert attr.app is app


@pytest.mark.parametrize('attr_name', ['Event', 'ModelEvent'])
def test_Event__pickle(attr_name, app):
    attr = getattr(app, attr_name)
    event = attr('article.created')
    assert pickle.loads(pickle.dumps(event)).app is app


def test_Request(app):
    request = app.Request('x.y', {}, None, Mock(name='subscriber'))
    assert isinstance(request, app.Request)
    assert isinstance(request, Request)
    assert request.app is app
    assert app.Request.app is app


def test_Request__pickle(app):
    request = app.Request('x.y', {}, None, Subscriber())
    request2 = pickle.loads(pickle.dumps(request))
    assert request2.app is app


def test_webhook_model(app):
    assert app.webhook_model is webhook_model


def test_model_reverser(app):
    assert app.model_reverser is model_reverser


def test_subclass_with_self__keep_reduce(app):
    class Object(object):
        app = None

        def __reduce__(self):
            return 303

    AppObject = app.subclass_with_self(Object, keep_reduce=True)
    assert AppObject().__reduce__() == 303


class test_buffering:

    def test_enable_buffer(self, app):
        app.dispatcher = Mock(name='dispatcher')
        app.enable_buffer(owner=id(app))
        app.dispatcher.enable_buffer.assert_called_once_with(owner=id(app))

    def test_dispable_buffer(self, app):
        app.dispatcher = Mock(name='dispatcher')
        app.disable_buffer(owner=id(app))
        app.dispatcher.disable_buffer.assert_called_once_with(owner=id(app))

    def test_flush_buffer(self, app):
        app.dispatcher = Mock(name='dispatcher')
        app.flush_buffer(owner=id(app))
        app.dispatcher.flush_buffer.assert_called_once_with(owner=id(app))
