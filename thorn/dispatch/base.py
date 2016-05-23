"""

    thorn.dispatch.base
    ===================

    Default webhook dispatcher.

"""
from __future__ import absolute_import, unicode_literals

from collections import Callable, deque
from itertools import chain

from celery.utils.functional import is_list, maybe_list
from vine import barrier

from thorn._state import app_or_default
from thorn.utils.compat import restore_from_keys

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

    def send(self, event, payload, sender, **kwargs):
        return barrier([
            self.dispatch_request(req) for req in self.prepare_requests(
                event, payload, sender, **kwargs
            )
        ])

    def dispatch_request(self, request):
        return request.dispatch()

    def prepare_requests(self, event, payload, sender,
                         timeout=None, **kwargs):
        # holds a cache of the payload serialized by content-type,
        # built incrementally depending on what content-types are
        # required by the subscribers.
        cache = {}
        timeout = timeout if timeout is not None else self.timeout
        return (
            self.app.Request(
                event,
                self.encode_cached(payload, cache, subscriber.content_type),
                sender, subscriber, timeout=timeout, **kwargs)
            for subscriber in self.subscribers_for_event(event, sender)
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

    def subscribers_for_event(self, name, sender=None):
        """Return a list of :class:`~thorn.django.models.Subscriber`
        subscribing to an event by name (optionally filtered by sender)."""
        return chain(*[source(name, sender=sender)
                       for source in self.subscriber_sources])

    def _configured_subscribers(self, name, sender=None):
        return [
            self.app.Subscriber.from_dict(d, event=name)
            for d in self._configured_for_event(name, sender=sender)
        ]

    def _configured_for_event(self, name, sender=None):
        stream = deque(
            maybe_list(self.app.settings.THORN_SUBSCRIBERS.get(name)) or []
        )
        while stream:
            for node in maybe_list(stream.popleft()):
                if isinstance(node, Callable):
                    node = node(name, sender=sender)
                if is_list(node):
                    stream.append(node)
                else:
                    yield node

    def _stored_subscribers(self, name, sender=None):
        return self.app.Subscribers.matching(event=name, user=sender)
