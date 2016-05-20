"""

    thorn.webhook.events
    ====================

    User-defined webhook events.

"""
from __future__ import absolute_import, unicode_literals

from operator import attrgetter
from six import iteritems as items, iterkeys as keys
from weakref import WeakSet

from ._state import app_or_default
from .utils.compat import bytes_if_py2, restore_from_keys
from .utils.functional import Q

__all__ = ['Event', 'ModelEvent']


def _true(*args, **kwargs):
    return True


class Event(object):
    """Webhook Event.

    :param name: Name of this event.
        Namespaces can be dot-separated, and if so subscribers can glob-match
        based on the parts in the name (e.g. ``"order.created"``).

    :keyword timeout: Default request timeout for this event.
    :keyword retry: Enable/disable retries when dispatching this event fails
        (disabled by default).
    :keyword retry_max: Max number of retries (3 by default).
    :keyword retry_delay: Delay between retries (60 seconds by default).
    :keyword recipient_validators: List of functions validating the recipient
        URL string.  Functions must return False if the URL is blocked.
        Default is to only allow HTTP and HTTPS, with respective reserved
        ports 80 and 443, and to block internal IP networks, and can
        be changed using the :setting:`THORN_RECIPIENT_VALIDATORS` setting::

            recipient_validators=[
                thorn.validators.block_internal_ips(),
                thorn.validators.ensure_protocol('http', 'https'),
                thorn.validators.ensure_port(80, 443),
            ]

        WARNING: :func:`~thorn.validators.block_internal_ips` will only
        test for reserved internal networks, and not private networks
        with a public IP address.  You can block those using
        :class:`~thorn.validators.block_cidr_network`.

        """
    app = None

    def __init__(self, name,
                 timeout=None, dispatcher=None,
                 retry=None, retry_max=None, retry_delay=None, app=None,
                 recipient_validators=None,
                 **kwargs):
        self.name = name
        self.timeout = timeout
        self._dispatcher = dispatcher
        self.retry = retry
        self.retry_max = retry_max
        self.retry_delay = retry_delay
        self.recipient_validators = recipient_validators
        self.app = app_or_default(app or self.app)

    def send(self, data, sender=None,
             on_success=None, on_error=None, timeout=None, on_timeout=None):
        """Send event to all subscribers.

        :param data: Event payload (must be json serializable).

        :keyword sender: Optional event sender, as a
            :class:`~django.contrib.auth.models.User` instance.
        :keyword timeout: Specify custom HTTP request timeout
            overriding the :setting:`THORN_EVENT_TIMEOUT` setting.

        :keyword on_success: Callback called for each HTTP request
            if the request succeeds.  Must take single
            :class:`~thorn.request.Request` argument.
        :keyword on_timeout: Callback called for each HTTP request
            if the request times out.  Takes two arguments:
            a :class:`~thorn.request.Request`, and the time out
            exception instance.
        :keyword on_error: Callback called for each HTTP request
            if the request fails.  Takes two arguments:
            a :class:`~thorn.request.Request` argument, and
            the error exception instance.

        """
        return self._send(
            data,
            sender=sender, on_success=on_success, on_error=on_error,
            timeout=timeout, on_timeout=on_timeout,
        )

    def _send(self, data, sender=None,
              on_success=None, on_error=None, timeout=None, on_timeout=None):
        timeout = timeout if timeout is not None else self.timeout
        return self.dispatcher.send(
            self.name, data, sender,
            on_success=on_success, on_error=on_error,
            timeout=timeout, on_timeout=on_timeout, retry=self.retry,
            retry_max=self.retry_max, retry_delay=self.retry_delay,
            recipient_validators=self.recipient_validators,
        )

    def __repr__(self):
        return bytes_if_py2("<{0}: {1} ({2:#x})>".format(
            type(self).__name__, self.name, id(self)))

    def __reduce__(self):
        return restore_from_keys, (type(self), (), self.__reduce_keys__())

    def __reduce_keys__(self):
        return {
            'name': self.name,
            'timeout': self.timeout,
            'dispatcher': self._dispatcher,
            'retry': self.retry,
            'retry_max': self.retry_max,
            'retry_delay': self.retry_delay,
        }

    @property
    def subscribers(self):
        return self.dispatcher.subscribers_for_event(self.name)

    @property
    def dispatcher(self):
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

    :param name: Name of event.
    :param reverse: A function that takes a model instance and returns
        the canonical URL for that resource.
    :keyword sender_field:
        Field used as a sender for events, e.g. ``"account.user"``,
        will use ``instance.account.user``.
    :keyword $field__$op: Optional filter arguments to filter the model
        instances to dispatch for.  These keyword arguments
        can be defined just like the arguments to a Django query set,
        the only difference being that you have to specify an operator
        for every field: this means ``last_name="jerry"`` does not work,
        and you have to use ``last_name__eq="jerry"`` instead.

        See :class:`~thorn.utils.functional.Q` for more information.

    :keyword signal_dispatcher: Custom
        :class:`~thorn.django.signals.signal_dispatcher` used to
        connect this event to a model signal.

    .. seealso:

        In addition the same arguments as :class:`Event` is supported.

    """
    signal_dispatcher = None

    def __init__(self, name, *args, **kwargs):
        super(ModelEvent, self).__init__(name, **kwargs)
        self._kwargs = kwargs
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

    def _init_attrs(self, reverse=None, sender_field=None,
                    signal_dispatcher=None, **kwargs):
        self.reverse = reverse
        self.sender_field = sender_field
        self.signal_dispatcher = signal_dispatcher

    def send(self, instance, data=None, sender=None, **kwargs):
        """Send event for model ``instance``.

        :keyword data: Event specific data.

        See :meth:`Event.send` for more arguments supported.

        """
        return self._send(self.to_message(
            data,
            sender=sender,
            ref=self.reverse(instance, app=self.app) if self.reverse else None,
        ), sender=sender, **kwargs)

    def send_from_instance(self, instance):
        return self.send(
            instance=instance,
            data=self.instance_data(instance),
            sender=self.instance_sender(instance),
        )

    def to_message(self, data, sender=None, ref=None):
        return {
            'event': self.name,
            'ref': ref,
            'sender': sender.get_username() if sender else sender,
            'data': data or {},
        }

    def instance_data(self, instance):
        """Get event data from ``instance.webhook_payload()``."""
        try:
            handler = instance.webhook_payload
        except AttributeError:
            pass
        else:
            return handler()

    def instance_sender(self, instance):
        """Get event ``sender`` from model instance."""
        if self.sender_field:
            return attrgetter(self.sender_field)(instance)

    def connect_model(self, model):
        self.models.add(model)
        self._connect_model_signal(model)

    def _connect_model_signal(self, model):
        if self.signal_dispatcher:
            self.signal_dispatcher.connect(sender=model)

    def should_dispatch(self, instance, **kwargs):
        return self._filter_predicate(instance)

    def on_signal(self, instance, **kwargs):
        if self.should_dispatch(instance, **kwargs):
            return self.send_from_instance(instance)

    def dispatches_on_create(self):
        return self._set_default_signal_dispatcher(
            self.app.signals.dispatch_on_create)

    def dispatches_on_change(self):
        return self._set_default_signal_dispatcher(
            self.app.signals.dispatch_on_change)

    def dispatches_on_delete(self):
        return self._set_default_signal_dispatcher(
            self.app.signals.dispatch_on_delete)

    def dispatches_on_m2m_add(self, related_field):
        return self._set_default_signal_dispatcher(
            self.app.signals.dispatch_on_m2m_add, related_field)

    def dispatches_on_m2m_remove(self, related_field):
        return self._set_default_signal_dispatcher(
            self.app.signals.dispatch_on_m2m_remove, related_field)

    def dispatches_on_m2m_clear(self, related_field):
        return self._set_default_signal_dispatcher(
            self.app.signals.dispatch_on_m2m_clear, related_field)

    def _set_default_signal_dispatcher(self, signal_dispatcher, *args):
        if self._signal_dispatcher is None:
            self._signal_dispatcher = self._prepare_signal_dispatcher(
                signal_dispatcher, *args)
        return self

    def __reduce_keys__(self):
        return dict(self._kwargs, name=self.name, _filterargs=self._filterargs)

    def _prepare_signal_dispatcher(self, signal_dispatcher, *args):
        d = signal_dispatcher(self.on_signal, *args)
        d.use_transitions = self.use_transitions
        return d

    @property
    def signal_dispatcher(self):
        return self._signal_dispatcher

    @signal_dispatcher.setter
    def signal_dispatcher(self, signal_dispatcher):
        self._signal_dispatcher = (
            self._prepare_signal_dispatcher(signal_dispatcher)
            if signal_dispatcher is not None else None
        )
