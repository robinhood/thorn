from __future__ import absolute_import, unicode_literals

from operator import attrgetter, methodcaller

from celery.utils import cached_property
from celery.utils.imports import symbol_by_name
from celery.utils.functional import first

from . import _state
from .utils.compat import bytes_if_py2


def _unpickle_appattr(reverse_name, kwargs):
    return attrgetter(reverse_name)(_state.current_app())(**kwargs)


class Thorn(object):
    event_cls = 'thorn.events:Event'
    model_event_cls = 'thorn.events:ModelEvent'
    settings_cls = 'thorn.conf:Settings'
    request_cls = 'thorn.request:Request'

    dispatchers = {
        'default': 'thorn.dispatch.base:Dispatcher',
        'celery': 'thorn.dispatch.celery:Dispatcher',
        'disabled': 'thorn.dispatch.disabled:Dispatcher',
    }
    environments = {
        'thorn.environment.django:DjangoEnv',
    }

    def __init__(self, dispatcher=None, set_as_current=True):
        self._dispatcher = dispatcher
        if set_as_current:
            self.set_current()

    def set_current(self):
        _state.set_current_app(self)

    def set_default(self):
        _state.set_default_app(self)

    def autodetect_env(self, apply=methodcaller('autodetect')):
        return first(apply, map(symbol_by_name, self.environments))()

    def _get_dispatcher(self, dispatcher=None):
        if dispatcher is None:
            dispatcher = self.settings.THORN_DISPATCHER
        return symbol_by_name(dispatcher, self.dispatchers)

    @cached_property
    def dispatcher(self):
        return self.Dispatcher()

    @cached_property
    def Dispatcher(self):
        return self.subclass_with_self(self._get_dispatcher(self._dispatcher))

    @property
    def config(self):
        return self.env.config

    @property
    def Subscriber(self):
        return self.env.Subscriber

    @property
    def Subscribers(self):
        return self.env.Subscribers

    @property
    def signals(self):
        return self.env.signals

    @property
    def reverse(self):
        return self.env.reverse

    @cached_property
    def Settings(self):
        return self.subclass_with_self(self.settings_cls)

    @cached_property
    def settings(self):
        return self.Settings()

    @cached_property
    def env(self):
        return self.autodetect_env()

    @cached_property
    def Event(self):
        return self.subclass_with_self(self.event_cls)

    @cached_property
    def ModelEvent(self):
        return self.subclass_with_self(self.model_event_cls)

    @cached_property
    def webhook_model(self):
        return symbol_by_name('thorn.decorators.webhook_model')

    @cached_property
    def model_reverser(self):
        return symbol_by_name('thorn.reverse.model_reverser')

    @cached_property
    def Request(self):
        return self.subclass_with_self(self.request_cls)

    def subclass_with_self(self, Class,
                           name=None, attribute='app',
                           reverse=None, keep_reduce=False, **kw):
        """Subclass an app-compatible class by setting its app attribute
        to this instance.

        App-compatible means the class has an 'app' attribute providing
        the default app, e.g.: ``class Foo(object): app = None``.

        :param Class: The class to subclass.
        :keyword name: Custom name for the target subclass.
        :keyword attribute: Name of the attribute holding the app.
            Default is ``"app"``.
        :keyword reverse: Reverse path to this object used for pickling
            purposes.  E.g. for ``app.AsyncResult`` use ``"AsyncResult"``.
        :keyword keep_reduce: If enabled a custom ``__reduce__`` implementation
           will not be provided.

        """
        Class = symbol_by_name(Class)
        reverse = reverse if reverse else Class.__name__

        def __reduce__(self):
            return _unpickle_appattr, (reverse, self.__reduce_keys__())

        attrs = dict({attribute: self},
                     __module__=Class.__module__,
                     __doc__=Class.__doc__,
                     **kw)
        if not keep_reduce:
            attrs['__reduce__'] = __reduce__

        return type(bytes_if_py2(name or Class.__name__), (Class,), attrs)
