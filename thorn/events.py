"""User-defined webhook events."""
from __future__ import absolute_import, unicode_literals

from operator import attrgetter
from six import iteritems as items, iterkeys as keys
from weakref import WeakSet

from celery.utils import cached_property

from ._state import app_or_default
from .utils.compat import bytes_if_py2, restore_from_keys
from .utils.functional import Q
from .utils.log import get_logger

__all__ = ['Event', 'ModelEvent']

E_DISPATCH_RAISED_ERROR = 'Event %r dispatch raised: %r'

logger = get_logger(__name__)


def _true(*args, **kwargs):
    # type: (*Any, **Any) -> bool
    return True


class Event(object):
    """Webhook Event.

    Arguments:
        name (str): Name of this event.
            Namespaces can be dot-separated, and if so subscribers can
            glob-match based on the parts in the name, e.g.
            ``"order.created"``.

    Keyword Arguments:
        timeout (float): Default request timeout for this event.
        retry (bool): Enable/disable retries when dispatching this event fails
            Disabled by default.
        retry_max (int): Max number of retries (3 by default).
        retry_delay (float): Delay between retries (60 seconds by default).
        recipient_validators (Sequence): List of functions validating the
            recipient URL string.  Functions must raise an error if the URL is
            blocked.  Default is to only allow HTTP and HTTPS, with respective
            reserved ports 80 and 443, and to block internal IP networks, and
            can be changed using the :setting:`THORN_RECIPIENT_VALIDATORS`
            setting::

                recipient_validators=[
                    thorn.validators.block_internal_ips(),
                    thorn.validators.ensure_protocol('http', 'https'),
                    thorn.validators.ensure_port(80, 443),
                ]
        subscribers: Additional subscribers, as a list of URLs,
            subscriber model objects, or callback functions returning these
        request_data: Optional mapping of extra data to inject into
            event payloads,
        allow_keepalive: Flag to disable HTTP connection keepalive
            for this event only.  Keepalive is enabled by default.

    Warning:
        :func:`~thorn.validators.block_internal_ips` will only
        test for reserved internal networks, and not private networks
        with a public IP address.  You can block those using
        :class:`~thorn.validators.block_cidr_network`.
    """

    app = None
    allow_keepalive = True
    recipient_validators = None

    def __init__(self, name,
                 timeout=None, dispatcher=None,
                 retry=None, retry_max=None, retry_delay=None, app=None,
                 recipient_validators=None, subscribers=None,
                 request_data=None, allow_keepalive=None,
                 **kwargs):
        # type: (str, float, Dispatcher, bool, int, float, App, List, Mapping, Dict, bool) -> None
        self.name = name
        self.timeout = timeout
        self._dispatcher = dispatcher
        self.retry = retry
        self.retry_max = retry_max
        self.retry_delay = retry_delay
        self.request_data = request_data
        if allow_keepalive is not None:
            self.allow_keepalive = allow_keepalive
        if recipient_validators is not None:
            self.recipient_validators = recipient_validators
        self._subscribers = subscribers
        self.app = app_or_default(app or self.app)

    def send(self, data, sender=None,
             on_success=None, on_error=None, timeout=None, on_timeout=None):
        # type: (Any, Any, Callable, Callable, float, Callable) -> promise
        """Send event to all subscribers.

        Arguments:
            data (Any): Event payload (must be json serializable).

        Keyword Arguments:
            sender (Any): Optional event sender, as a
                :class:`~django.contrib.auth.models.User` instance.
            context (Dict): Extra context to pass to subscriber callbacks.
            timeout (float): Specify custom HTTP request timeout
                overriding the :setting:`THORN_EVENT_TIMEOUT` setting.

            on_success (Callable): Callback called for each HTTP request
                if the request succeeds.  Must take single
                :class:`~thorn.request.Request` argument.
            on_timeout (Callable): Callback called for each HTTP request
                if the request times out.  Takes two arguments:
                a :class:`~thorn.request.Request`, and the time out
                exception instance.
            on_error (Callable): Callback called for each HTTP request
                if the request fails.  Takes two arguments:
                a :class:`~thorn.request.Request` argument, and
                the error exception instance.
        """
        return self._send(
            self.name, data,
            sender=sender, on_success=on_success, on_error=on_error,
            timeout=timeout, on_timeout=on_timeout,
        )

    def prepare_payload(self, data):
        # type: (Any) -> Any
        return dict(self.request_data, **data) if self.request_data else data

    def _send(self, name, data, headers=None, sender=None,
              on_success=None, on_error=None,
              timeout=None, on_timeout=None, context=None):
        # type: (str, Any, Dict, Any, Callable, Callable, float, Callable, Dict) -> promise
        timeout = timeout if timeout is not None else self.timeout
        return self.dispatcher.send(
            name, self.prepare_payload(data), sender,
            headers=headers,
            context=context,
            on_success=on_success, on_error=on_error,
            timeout=timeout, on_timeout=on_timeout, retry=self.retry,
            retry_max=self.retry_max, retry_delay=self.retry_delay,
            recipient_validators=self.prepared_recipient_validators,
            extra_subscribers=self._subscribers,
            allow_keepalive=self.allow_keepalive,
        )

    def __repr__(self):
        # type: () -> str
        return bytes_if_py2('<{0}: {1} ({2:#x})>'.format(
            type(self).__name__, self.name, id(self)))

    def __reduce__(self):
        return restore_from_keys, (type(self), (), self.__reduce_keys__())

    def __reduce_keys__(self):
        # type: () -> Dict[str, Any]
        return {
            'name': self.name,
            'timeout': self.timeout,
            'dispatcher': self._dispatcher,
            'retry': self.retry,
            'retry_max': self.retry_max,
            'retry_delay': self.retry_delay,
            'subscribers': self._subscribers,
            'request_data': self.request_data,
            'allow_keepalive': self.allow_keepalive,
        }

    def prepare_recipient_validators(self, validators):
        # type: (Sequence[Callable]) -> Sequence[Callable]
        """Prepare recipient validator list (instance-wide).

        Note:
            This value will be cached
        Return v

        """
        return validators

    @cached_property
    def prepared_recipient_validators(self):
        # type: () -> Sequence[Callable]
        return self.prepare_recipient_validators(self.recipient_validators)

    @property
    def subscribers(self):
        # type: () -> Sequence[Subscriber]
        return self.dispatcher.subscribers_for_event(
            self.name, extra_subscribers=self._subscribers,
        )

    @subscribers.setter
    def subscribers(self, subscribers):
        # type: (Sequence[Subscriber]) -> None
        self._subscribers = subscribers

    @property
    def dispatcher(self):
        # type: () -> Dispatcher
        return (self._dispatcher if self._dispatcher is not None
                else self.app.dispatcher)


class ModelEvent(Event):
    """Event related to model changes.

    This event type follows a specific payload format:

    .. code-block:: json

        {"event": "(str)event_name",
         "ref": "(URL)model_location",
         "sender": "(User pk)optional_sender",
         "data": {"event specific data": "value"}}

    Arguments:
        name (str): Name of event.

    Keyword Arguments:
        reverse (Callable): A function that takes a model instance and returns
            the canonical URL for that resource.
        sender_field (str):
            Field used as a sender for events, e.g. ``"account.user"``,
            will use ``instance.account.user``.
        signal_honors_transaction(bool): If enabled the webhook dispatch
            will be tied to any current database transaction:
            webhook is sent on transaction commit, and ignored if the
            transaction rolls back.

            Default is True (taken from the
                :setting:`THORN_SIGNAL_HONORS_TRANSACTION` setting), but
            requires Django 1.9 or greater.  Earlier Django versions will
            execute the dispatch immediately.

            .. versionadded:: 1.5

        propagate_errors (bool): If enabled errors will propagate
            up to the caller (even when called by signal).

            Disabled by default.

            .. versionadded:: 1.5

        signal_dispatcher (~thorn.django.signals.signal_dispatcher):
            Custom signal_dispatcher used to connect this event to a
            model signal.
        $field__$op (Any): Optional filter arguments to filter the model
            instances to dispatch for.  These keyword arguments
            can be defined just like the arguments to a Django query set,
            the only difference being that you have to specify an operator
            for every field: this means ``last_name="jerry"`` does not work,
            and you have to use ``last_name__eq="jerry"`` instead.

            See :class:`~thorn.utils.functional.Q` for more information.

    See Also:
        In addition the same arguments as :class:`Event` is supported.
    """

    signal_dispatcher = None  # type: signal_dispatcher

    def __init__(self, name, *args, **kwargs):
        # type: (str, *Any, **Any) -> None
        super(ModelEvent, self).__init__(name, **kwargs)
        self._kwargs = kwargs
        self._kwargs.pop('app', None)  # don't use app in __reduce__
        self._filterargs = args

        self.models = WeakSet()

        # initialize the filter fields: {field}__{op}
        self.filter_fields = {
            k: v for k, v in items(kwargs) if '__' in k
        }
        # optimization: Django: Transition operators require the unchanged
        # database fields before saving, a pre_save signal
        # handles this, but we want to avoid the extra database hit
        # when they are not in use.
        self.use_transitions = any(
            '__now_' in k for k in keys(self.filter_fields),
        )
        # _filterargs is set by __reduce__ to restore *args
        restored_args = kwargs.get('_filterargs') or ()
        self._init_attrs(**kwargs)
        self._filter_predicate = (
            Q(*args + restored_args, **self.filter_fields)
            if args or self.filter_fields else _true)

    def _init_attrs(self,
                    reverse=None,
                    sender_field=None,
                    signal_dispatcher=None,
                    signal_honors_transaction=None,
                    propagate_errors=False,
                    **kwargs):
        # type: (model_reverser, str, signal_dispatcher, bool, bool, **Any) -> None
        self.reverse = reverse
        self.sender_field = sender_field
        self.signal_dispatcher = signal_dispatcher
        self._signal_honors_transaction = signal_honors_transaction
        self.propagate_errors = propagate_errors

    def _get_name(self, instance):
        # type: (Model) -> str
        """Interpolate event name with attributes from the instance."""
        return self.name.format(instance)

    def send(self, instance, data=None, sender=None, **kwargs):
        # type: (Model, Any, Any, **Any) -> promise
        """Send event for model ``instance``.

        Keyword Arguments:
            data (Any): Event specific data.

        See Also:
            :meth:`Event.send` for more arguments supported.
        """
        name = self._get_name(instance)
        return self._send(name, self.to_message(
            data,
            instance=instance,
            sender=sender,
            ref=self.get_absolute_url(instance),
        ), sender=sender, **kwargs)

    def get_absolute_url(self, instance):
        # type: (Model) -> Optional[str]
        return (
            self._get_absolute_url_from_reverse(instance) or
            self._get_absolute_url_from_model(instance)
        )

    def _get_absolute_url_from_reverse(self, instance):
        # type: (Model) -> Optional[str]
        if self.reverse is not None:
            return self.reverse(instance, app=self.app)

    def _get_absolute_url_from_model(self, instance):
        # type: (Model) -> Optional[str]
        try:
            absurl = instance.get_absolute_url
        except AttributeError:
            pass
        else:
            return absurl()

    def send_from_instance(self, instance, context={}, **kwargs):
        # type: (Model, Mapping, **Any) -> promise
        return self.send(
            instance=instance,
            headers=self.instance_headers(instance),
            data=self.instance_data(instance),
            sender=self.instance_sender(instance),
            context=context,
        )

    def to_message(self, data, instance=None, sender=None, ref=None):
        # type: (Any, Model, Any, str) -> Dict[str, Any]
        name = self._get_name(instance)
        return {
            'event': name,
            'ref': ref,
            'sender': sender.get_username() if sender else sender,
            'data': data or {},
        }

    def instance_data(self, instance):
        # type: (Model) -> Any
        """Get event data from ``instance.webhooks.payload()``."""
        return instance.webhooks.payload(instance)

    def instance_headers(self, instance):
        # type: (Model) -> Mapping
        """Get event headers from ``instance.webhooks.headers()``."""
        return instance.webhooks.headers(instance)

    def instance_sender(self, instance):
        # type: (Model) -> Any
        """Get event ``sender`` from model instance."""
        if self.sender_field:
            return attrgetter(self.sender_field)(instance)

    def connect_model(self, model):
        # type: (Any) -> None
        self.models.add(model)
        self._connect_model_signal(model)

    def _connect_model_signal(self, model):
        # type: (Any) -> None
        if self.signal_dispatcher:
            self.signal_dispatcher.connect(sender=model)

    def should_dispatch(self, instance, **kwargs):
        # type: (Model, **Any) -> bool
        return self._filter_predicate(instance)

    def on_signal(self, instance, **kwargs):
        # type: (Model, **Any) -> promise
        if self.signal_honors_transaction:
            return self.app.on_commit(self._on_signal, instance, kwargs)
        return self._on_signal(instance, kwargs)

    def _on_signal(self, instance, kwargs):
        # type (Model, Dict) -> promise
        try:
            if self.should_dispatch(instance, **kwargs):
                return self.send_from_instance(instance, **kwargs)
        except Exception as exc:
            if self.propagate_errors:
                raise
            logger.exception(E_DISPATCH_RAISED_ERROR, self.name, exc)

    def dispatches_on_create(self):
        # type: () -> Event
        return self._set_default_signal_dispatcher(
            self.app.signals.dispatch_on_create)

    def dispatches_on_change(self):
        # type: () -> Event
        return self._set_default_signal_dispatcher(
            self.app.signals.dispatch_on_change)

    def dispatches_on_delete(self):
        # type: () -> Event
        return self._set_default_signal_dispatcher(
            self.app.signals.dispatch_on_delete)

    def dispatches_on_m2m_add(self, related_field):
        # type: () -> Event
        return self._set_default_signal_dispatcher(
            self.app.signals.dispatch_on_m2m_add, related_field)

    def dispatches_on_m2m_remove(self, related_field):
        # type: () -> Event
        return self._set_default_signal_dispatcher(
            self.app.signals.dispatch_on_m2m_remove, related_field)

    def dispatches_on_m2m_clear(self, related_field):
        # type: () -> Event
        return self._set_default_signal_dispatcher(
            self.app.signals.dispatch_on_m2m_clear, related_field)

    def _set_default_signal_dispatcher(self, signal_dispatcher, *args):
        # type: (signal_dispatcher, *Any) -> Event
        if self._signal_dispatcher is None:
            self._signal_dispatcher = self._prepare_signal_dispatcher(
                signal_dispatcher, *args)
        return self

    def __reduce_keys__(self):
        # type: () -> Dict[str, Any]
        return dict(self._kwargs, name=self.name, _filterargs=self._filterargs)

    def _prepare_signal_dispatcher(self, signal_dispatcher, *args):
        # type: (type) -> signal_dispatcher
        d = signal_dispatcher(self.on_signal, *args)
        d.use_transitions = self.use_transitions
        return d

    @property
    def signal_dispatcher(self):
        # type: () -> signal_dispatcher
        return self._signal_dispatcher

    @signal_dispatcher.setter
    def signal_dispatcher(self, signal_dispatcher):
        # type: (signal_dispatcher) -> None
        self._signal_dispatcher = (
            self._prepare_signal_dispatcher(signal_dispatcher)
            if signal_dispatcher is not None else None
        )

    @cached_property
    def signal_honors_transaction(self):
        if self._signal_honors_transaction is None:
            return self.app.settings.THORN_SIGNAL_HONORS_TRANSACTION
        return self._signal_honors_transaction
