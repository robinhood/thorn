"""Celery-based webhook dispatcher."""
from __future__ import absolute_import, unicode_literals

from celery import group

from thorn.tasks import send_event, dispatch_requests
from thorn.utils.functional import chunks

from . import base

__all__ = ['Dispatcher', 'WorkerDispatcher']


class _CeleryDispatcher(base.Dispatcher):

    def as_request_group(self, requests):
        return group(
            dispatch_requests.s([req.as_dict() for req in chunk])
            for chunk in self.group_requests(requests)
        )

    def group_requests(self, requests):
        """Group requests by keep-alive host/port/scheme ident."""
        return chunks(iter(requests), self.app.settings.THORN_CHUNKSIZE)

    def _compare_requests(self, a, b):
        return a.urlident == b.urlident


class Dispatcher(_CeleryDispatcher):
    """Dispatcher using Celery tasks to dispatch events.

    Note:
        Overrides what happens when :meth:`thorn.webhook.Event.send` is
        called so that dispatching the HTTP request tasks is performed by
        a worker, instead of in the current process.
    """

    def send(self, event, payload, sender,
             timeout=None, context=None, **kwargs):
        return send_event.s(
            event, payload,
            sender.pk if sender else sender, timeout, context,
        ).apply_async()

    def flush_buffer(self):
        # XXX Not thread-safe
        g = self.as_request_group(self.pending_outbound)
        self.pending_outbound.clear()
        g.delay()


class WorkerDispatcher(_CeleryDispatcher):
    """Dispatcher used by the :func:`thorn.tasks.send_event` task."""

    def send(self, event, payload, sender,
             timeout=None, context=None, **kwargs):
        # the requests are sorted by url, so we group them into chunks
        # each containing a list of requests for that host/port/scheme pair,
        # with up to :setting:`THORN_CHUNKSIZE` requests each.
        #
        # this way requests have a good chance of reusing keepalive
        # connections as requests with the same host are grouped together.
        return self.as_request_group(self.prepare_requests(
            event, payload, sender, timeout, context, **kwargs)).delay()
