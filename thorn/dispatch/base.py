"""

    thorn.dispatch.base
    ===================

    Default webhook dispatcher.

"""
from __future__ import absolute_import, unicode_literals

from functools import partial
from itertools import chain

from celery.utils.functional import maybe_list
from vine import barrier

from thorn._state import app_or_default
from thorn.generic.models import AbstractSubscriber
from thorn.utils.compat import restore_from_keys
from thorn.utils.functional import traverse_subscribers

__all__ = ['Dispatcher']


class Dispatcher(object):
    app = None

    def __init__(self, timeout=None, app=None):
        self.app = app_or_default(app or self.app)
        self.timeout = (
            timeout if timeout is not None
            else self.app.settings.THORN_EVENT_TIMEOUT
        )
        self.subscriber_sources = [
            self._configured_subscribers,
            self._stored_subscribers,
        ]

    def __reduce__(self):
        return restore_from_keys, (type(self), (), self.__reduce_keys__())

    def __reduce_keys__(self):
        return {'timeout': self.timeout}

    def send(self, event, payload, sender,
             context=None, extra_subscribers=None,
             allow_keepalive=True, **kwargs):
        return barrier([
            self.dispatch_request(req) for req in self.prepare_requests(
                event, payload, sender,
                context=context or {},
                extra_subscribers=extra_subscribers,
                allow_keepalive=allow_keepalive,
                **kwargs
            )
        ])

    def dispatch_request(self, request):
        return request.dispatch()

    def prepare_requests(self, event, payload, sender,
                         timeout=None, context=None,
                         extra_subscribers=None, **kwargs):
        # holds a cache of the payload serialized by content-type,
        # built incrementally depending on what content-types are
        # required by the subscribers.
        cache = {}
        timeout = timeout if timeout is not None else self.timeout
        context = context or {}
        return (
            self.app.Request(
                event,
                self.encode_cached(payload, cache, subscriber.content_type),
                sender, subscriber,
                timeout=timeout, **kwargs)
            for subscriber in self.subscribers_for_event(
                event, sender, context, extra_subscribers)
        )

    def encode_cached(self, payload, cache, ctype):
        try:
            return cache[ctype]
        except KeyError:
            value = cache[ctype] = self.encode_payload(payload, ctype)
            return value

    def encode_payload(self, data, content_type):
        try:
            encode = self.app.settings.THORN_CODECS[content_type]
        except KeyError:
            return data
        else:
            return encode(data)

    def subscribers_for_event(self, name,
                              sender=None, context={}, extra_subscribers=None):
        """Return a list of :class:`~thorn.django.models.Subscriber`
        subscribing to an event by name (optionally filtered by sender)."""
        return chain(*[
            source(name, sender=sender, **context)
            for source in chain(
                self.subscriber_sources,
                [partial(self._traverse_subscribers, extra_subscribers or [])],
            )
        ])

    def _maybe_subscriber(self, d, **kwargs):
        return (self.app.Subscriber.from_dict(d, **kwargs)
                if not isinstance(d, AbstractSubscriber) else d)

    def _traverse_subscribers(self, it, name, **context):
        return (self._maybe_subscriber(d, event=name)
                for d in traverse_subscribers(it, name, **context))

    def _configured_subscribers(self, name, **context):
        return self._configured_for_event(name, **context)

    def _configured_for_event(self, name, **context):
        return self._traverse_subscribers(
            maybe_list(self.app.settings.THORN_SUBSCRIBERS.get(name)) or [],
            name, **context)

    def _stored_subscribers(self, name, sender=None, **context):
        return self.app.Subscribers.matching(event=name, user=sender)
