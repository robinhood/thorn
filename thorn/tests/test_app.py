from __future__ import absolute_import, unicode_literals

import pickle
import thorn.dispatch.disabled
import thorn.dispatch.base

from thorn import Thorn
from thorn.decorators import webhook_model
from thorn.events import Event, ModelEvent
from thorn.reverse import model_reverser
from thorn.request import Request

from .case import Mock, ThornCase, patch


class Subscriber(object):

    def as_dict(self):
        return {}


class test_Thorn(ThornCase):

    @patch('thorn._state.set_default_app')
    def test_set_default(self, set_default_app):
        self.app.set_default()
        set_default_app.assert_called_once_with(self.app)

    def test_dispatcher__argument(self):

        class Dispatcher(object):
            app = None

        app = Thorn(set_as_current=False, dispatcher=Dispatcher)
        self.assertIsInstance(app.dispatcher, Dispatcher)
        self.assertIs(app.dispatcher.app, app)

    def test_dispatcher__setting(self):
        self.app.settings.THORN_DISPATCHER = 'disabled'
        self.assertIsInstance(
            self.app.dispatcher, thorn.dispatch.disabled.Dispatcher,
        )
        self.assertIs(self.app.dispatcher.app, self.app)

    def test_dispatcher__default(self):
        self.assertIsInstance(
            self.app.dispatcher, thorn.dispatch.base.Dispatcher,
        )

    def test_dispatcher__pickle(self):
        self.assertIs(
            pickle.loads(pickle.dumps(self.app.dispatcher)).app,
            self.app,
        )

    def test_Subscriber(self):
        self.app.env = Mock(name='env')
        self.assertIs(self.app.Subscriber, self.app.env.Subscriber)

    def test_Subscribers(self):
        self.app.env = Mock(name='env')
        self.assertIs(self.app.Subscribers, self.app.env.Subscribers)

    def test_signals(self):
        self.app.env = Mock(name='env')
        self.assertIs(self.app.signals, self.app.env.signals)

    def test_reverse(self):
        self.app.env = Mock(name='env')
        self.assertIs(self.app.reverse, self.app.env.reverse)

    def test_Event(self):
        event = self.app.Event('article.created')
        self.assertIsInstance(event, self.app.Event)
        self.assertIsInstance(event, Event)
        self.assertIs(event.app, self.app)
        self.assertIs(self.app.Event.app, self.app)

    def test_Event__pickle(self):
        event = self.app.Event('article.created')
        self.assertIs(pickle.loads(pickle.dumps(event)).app, self.app)

    def test_ModelEvent(self):
        event = self.app.ModelEvent('article.created')
        self.assertIsInstance(event, self.app.ModelEvent)
        self.assertIsInstance(event, ModelEvent)
        self.assertIs(event.app, self.app)
        self.assertIs(self.app.ModelEvent.app, self.app)

    def test_ModelEvent__pickle(self):
        event = self.app.ModelEvent('article.created')
        self.assertIs(pickle.loads(pickle.dumps(event)).app, self.app)

    def test_Request(self):
        request = self.app.Request('x.y', {}, None, Mock(name='subscriber'))
        self.assertIsInstance(request, self.app.Request)
        self.assertIsInstance(request, Request)
        self.assertIs(request.app, self.app)
        self.assertIs(self.app.Request.app, self.app)

    def test_Request__pickle(self):
        request = self.app.Request('x.y', {}, None, Subscriber())
        request2 = pickle.loads(pickle.dumps(request))
        self.assertIs(request2.app, self.app)

    def test_webhook_model(self):
        self.assertIs(self.app.webhook_model, webhook_model)

    def test_model_reverser(self):
        self.assertIs(self.app.model_reverser, model_reverser)

    def test_subclass_with_self__keep_reduce(self):
        class Object(object):
            app = None

            def __reduce__(self):
                return 303

        AppObject = self.app.subclass_with_self(Object, keep_reduce=True)
        self.assertEqual(AppObject().__reduce__(), 303)
