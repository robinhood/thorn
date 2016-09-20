"""Tasks used by the Celery dispatcher."""
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.utils.functional import memoize

from ._state import app_or_default

__all__ = ['send_event', 'dispatch_requests', 'dispatch_request']


@memoize()
def _worker_dispatcher():
    # type: () -> Dispatcher
    from .dispatch.celery import WorkerDispatcher
    return WorkerDispatcher()


@shared_task(ignore_result=True)
def send_event(event, payload, sender, timeout, context={}):
    # type: (str, Dict, Any, float, Dict) -> None
    """Task called by process dispatching the event.

    Note:
        This will use the WorkerDispatcher to dispatch the individual
        HTTP requests in batches (``dispatch_requests -> dispatch_request``).
    """
    _worker_dispatcher().send(
        event, payload, sender, timeout=timeout, context=context)


@shared_task(ignore_result=True)
def dispatch_requests(reqs, app=None):
    # type: (Sequence[Dict], App) -> None
    """Process a batch of HTTP requests."""
    app = app_or_default(app)
    session = app.Request.Session()
    [dispatch_request(session=session, app=app, **req) for req in reqs]


@shared_task(bind=True, ignore_result=True)
def dispatch_request(self, event, data, sender, subscriber,
                     session=None, app=None, **kwargs):
    # type: (str, Dict, Any, Dict, requests.Session, App, **Any) -> None
    """Process a single HTTP request."""
    app = app_or_default(app)
    # the user is serialized as the pk, so we cannot pass it
    # directly to Subscriber, but we also don't need it at this point.
    subscriber.pop('user', None)
    subscriber = app.Subscriber(**subscriber)
    request = app.Request(event, data, sender, subscriber, **kwargs)
    try:
        request.dispatch(session=session, propagate=request.retry)
    except request.connection_errors + request.timeout_errors as exc:
        if request.retry:
            raise self.retry(exc=exc, max_retries=request.retry_max,
                             countdown=request.retry_delay)
        raise
