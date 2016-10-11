"""Thorn Application."""
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
    """Thorn application."""

    event_cls = 'thorn.events:Event'
    model_event_cls = 'thorn.events:ModelEvent'
    settings_cls = 'thorn.conf:Settings'
    request_cls = 'thorn.request:Request'

    dispatchers = {  # type: Mapping[str, str]
        'default': 'thorn.dispatch.base:Dispatcher',
        'celery': 'thorn.dispatch.celery:Dispatcher',
        'disabled': 'thorn.dispatch.disabled:Dispatcher',
    }
    environments = {  # type: Set[str]
        'thorn.environment.django:DjangoEnv',
    }

    def __init__(self, dispatcher=None, set_as_current=True):
        # type: (Union[str, Dispatcher], bool) -> None
        self._dispatcher = dispatcher
        if set_as_current:
            self.set_current()

    def enable_buffer(self, owner=None):
        # type: () -> None
        """Start buffering up events instead of dispatching them directly.

        Note:
            User will be responsible for flushing the buffer via
            :meth:`flush_buffer`, say periodically or at the end of a
            web request.
        """
        self.dispatcher.enable_buffer(owner=owner)

    def disable_buffer(self, owner=None):
        # type: () -> None
        """Disable buffering.

        Raises:
            ~thorn.exceptions.BufferNotEmpty: if there are still items in the
            buffer when disabling.
        """
        self.dispatcher.disable_buffer(owner=owner)

    def flush_buffer(self, owner=None):
        # type: () -> None
        """Flush events accumulated while buffering active.

        Note:
            This will force send any buffered events, but the mechanics of how
            this happens is up to the dispatching backend:

            - ``default``

                Sends buffered events one by one.

            - ``celery``

                Sends a single message containing all buffered
                events, a worker will then pick that up and execute the
                web requests.
        """
        self.dispatcher.flush_buffer(owner=owner)

    def set_current(self):
        # type: () -> None
        _state.set_current_app(self)

    def set_default(self):
        # type: () -> None
        _state.set_default_app(self)

    def autodetect_env(self, apply=methodcaller('autodetect')):
        # type: (Callable) -> Any
        return first(apply, map(symbol_by_name, self.environments))()

    def _get_dispatcher(self, dispatcher=None):
        # type: (Union[str, Dispatcher]) -> Dispatcher
        if dispatcher is None:
            dispatcher = self.settings.THORN_DISPATCHER
        return symbol_by_name(dispatcher, self.dispatchers)

    @cached_property
    def dispatcher(self):
        # type: () -> Dispatcher
        return self.Dispatcher()

    @cached_property
    def Dispatcher(self):
        # type: () -> type
        return self.subclass_with_self(self._get_dispatcher(self._dispatcher))

    @cached_property
    def hmac_sign(self):
        # type: () -> Callable
        return symbol_by_name(self.settings.THORN_HMAC_SIGNER)

    @property
    def config(self):
        # type: () -> Any
        return self.env.config

    @property
    def on_commit(self):
        # type: () -> Callable
        return self.env.on_commit

    @property
    def Subscriber(self):
        # type: () -> type
        return self.env.Subscriber

    @property
    def Subscribers(self):
        # type: () -> type
        return self.env.Subscribers

    @property
    def signals(self):
        # type: () -> Any
        return self.env.signals

    @property
    def reverse(self):
        # type: () -> Callable
        return self.env.reverse

    @cached_property
    def Settings(self):
        # type: () -> type
        return self.subclass_with_self(self.settings_cls)

    @cached_property
    def settings(self):
        # type: () -> Settings
        return self.Settings()

    @cached_property
    def env(self):
        # type: () -> Env
        return self.autodetect_env()

    @cached_property
    def Event(self):
        # type: () -> type
        return self.subclass_with_self(self.event_cls)

    @cached_property
    def ModelEvent(self):
        # type: () -> type
        return self.subclass_with_self(self.model_event_cls)

    @cached_property
    def webhook_model(self):
        # type: () -> Callable
        return symbol_by_name('thorn.decorators.webhook_model')

    @cached_property
    def model_reverser(self):
        # type: () -> Callable
        return symbol_by_name('thorn.reverse.model_reverser')

    @cached_property
    def Request(self):
        # type: () -> type
        return self.subclass_with_self(self.request_cls)

    def subclass_with_self(self, Class,
                           name=None, attribute='app',
                           reverse=None, keep_reduce=False, **kw):
        # type: (type, str, str, str, bool, **Any) -> type
        """Subclass an app-compatible class.

        App-compatible means the class has an 'app' attribute providing
        the default app, e.g.: ``class Foo(object): app = None``.

        Arguments:
            Class (Any): The class to subclass.

        Keyword Arguments:
            name (str): Custom name for the target subclass.
            attribute (str): Name of the attribute holding the app.
                Default is ``"app"``.
            reverse (str): Reverse path to this object used for pickling
                purposes.  E.g. for ``app.AsyncResult`` use ``"AsyncResult"``.
            keep_reduce (bool): If enabled a custom ``__reduce__``
                implementation will not be provided.
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
