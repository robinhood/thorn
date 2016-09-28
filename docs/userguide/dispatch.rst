.. _dispatch-guide:

=============================================================================
                               Dispatch
=============================================================================

.. contents:: Table of Contents:
    :local:
    :depth: 1

Introduction
============

As soon as you call ``event.send`` the webhook will be dispatched
by performing HTTP requests to all the subscriber URL's matching the
event.

The dispatch mechanism is configurable, and even supports pluggable
backends.

There are three built-in dispatcher backends available:

- ``"default"``

    Dispatch requests directly in the current process.

    In a web server the HTTP request will not complete until
    all of the Webhook requests have finished, so this is only
    suited for use in small installations and in development
    environments.

- ``"disabled"``

    Does not dispatch requests at all, useful for development.

- ``"celery"``

    Dispatch requests by sending a single :pypi:`Celery` task for every
    event.  The task will then be received by a worker which will
    start sending requests in batches to subscribers.

    Since performing HTTP requests are entirely I/O bound, routing
    these tasks to workers running the :pypi:`eventlet` or :pypi:`gevent`
    pools are recommended (see :ref:`optimization-guide`).

    The HTTP requests are also sorted by URL so that requests for the
    same domain have a high chance of being routed to the same process,
    to benefit from connection keep-alive settings, etc.

To configure the dispatcher used you need to change the
:setting:`THORN_DISPATCHER` setting.

HTTP Client
===========

Thorn uses the :pypi:`requests` library to perform HTTP requests,
and will reuse a single :class:`~requests.Session` for every thread/process.

.. _dispatch-http-headers:

HTTP Headers
============

Thorn will provide the endpoints with standard HTTP header values

+-----------------------+--------------------------------------------------------+
| **Header**            | **Description**                                        |
+-----------------------+--------------------------------------------------------+
| ``Hook-Event``        | Name of the event that triggered this delivery.        |
+-----------------------+--------------------------------------------------------+
| ``Hook-Delivery``     | Unique id for this delivery.                           |
+-----------------------+--------------------------------------------------------+
| ``Hook-HMAC``         | HMAC digest that can be used to verify the sender      |
+-----------------------+--------------------------------------------------------+
| ``Hook-Subscription`` | Subscription UUID (can be used to cancel/modify)       |
+-----------------------+--------------------------------------------------------+
| ``User-Agent``        | User agent string, including Thorn and client version. |
+-----------------------+--------------------------------------------------------+
| ``Content-Type``      | Delivery content type (e.g. application/json).         |
+-----------------------+--------------------------------------------------------+

HTTPS/SSL Requests
==================

Thorn supports using ``https://`` URLs as callbacks, but for that to work
the destination web server must be properly configured for HTTPS and have
a valid server certificate.

.. _event-buffering:

Buffering
=========

By default Thorn will dispatch events as they happen, but you can also enable
event buffering:

.. code-block:: python

    import thorn

    with thorn.buffer_events():
        ...

All events sent within this block will be moved to a list, to be dispatched
as soon as the block exits, or the buffer is explicitly flushed.

If you want to flush the buffer manually, you may keep a reference to the
context:

.. code-block:: python

    with thorn.buffer_events() as buffer:
        Article.objects.create(...)
        Article.objects.create(...)
        buffer.flush()
        Article.objects.create(...)
        buffer.flush()

The dispatching backend decides what happens when you flush the buffer:

- ``celery`` dispatcher

    Flushing the buffer will chunk buffered requests together
    in sizes defined by the :setting:`THORN_CHUNKSIZE` setting.

    If the chunk size is 10 (default), this means 100 events will be delivered
    to workers in 10 messages.

- ``default`` dispatcher

    Flushing the buffer will send each event in turn, blocking
    the current process until all events have been sent.

.. admonition:: Nested contexts

    If you have nested ``buffer_events`` contexts, then only the outermost
    context will be active:

    .. code-block:: python

        with thorn.buffer_events():
            Article.objects.create(name='A')

            with thorn.buffer_events():
                Article.objects.create(name='B')
            # << context exit delegates flush to outermost buffering context.

            Article.objects.create(name='C')
        # << events for A, B, C dispatched here.

    Note that this does NOT apply if you call ``buffer.flush()`` manually:
    that will flush events from all contexts.

Periodic flush
--------------

The context can also be used to flush the buffer periodically, using the
``flush_freq`` and ``flush_timeout`` arguments together with the
``maybe_flush`` method:

.. code-block:: python

    # Only flush every 100 calls, or if two seconds passed since last flush.
    with thorn.buffer_events(flush_freq=100, flush_timeout=2.0) as buffer:
        for thing in things:
            process_thing_leading_to_webhook_being_sent(thing)
            buffer.maybe_flush()
