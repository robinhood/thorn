"""

    thorn.dispatch.celery
    =====================

    Celery-based webhook dispatcher.

"""
from __future__ import absolute_import, unicode_literals

from celery import group

from thorn.tasks import send_event, dispatch_requests
from thorn.utils.functional import groupbymax

from . import base

__all__ = ['Dispatcher', 'WorkerDispatcher']


class Dispatcher(base.Dispatcher):
    """Dispatcher using Celery tasks to dispatch events.

    Overrides what happens when :meth:`thorn.webhook.Event.send` is called
    so that dispatching the HTTP request tasks is performed by a worker,
    instead of in the current process.

    """

    def send(self, event, payload, sender, timeout=None, **kwargs):
        return send_event.s(
            event, payload,
            sender.pk if sender else sender, timeout,
        ).apply_async()


class WorkerDispatcher(base.Dispatcher):
    """Dispatcher used by the :func:`thorn.tasks.send_event` task."""

    def send(self, event, payload, sender, timeout=None, **kwargs):
        # the requests are sorted by url, so we group them into chunks
        # each containing a list of requests for that host/port/scheme pair,
        # with up to :setting:`THORN_CHUNKSIZE` requests each.
        #
        # this way requests have a good chance of reusing keepalive
        # connections as requests with the same host are grouped together.
        return group(
            dispatch_requests.s([req.as_dict() for req in chunk])
            for chunk in self.group_requests(
                self.prepare_requests(event, payload, sender, timeout))
        ).delay()

    def group_requests(self, requests):
        """Group requests by keep-alive host/port/scheme ident."""
        return groupbymax(
            requests,
            max=self.app.settings.THORN_CHUNKSIZE,
            key=self._compare_requests,
        )

    def _compare_requests(self, a, b):
        return a.urlident == b.urlident
