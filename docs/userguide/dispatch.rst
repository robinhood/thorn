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

+-------------------+--------------------------------------------------------+
| **Header**        | **Description**                                        |
+-------------------+--------------------------------------------------------+
| ``Hook-Event``    | Name of the event that triggered this delivery.        |
+-------------------+--------------------------------------------------------+
| ``Hook-Delivery`` | Unique id for this delivery.                           |
+-------------------+--------------------------------------------------------+
| ``Hook-HMAC``     | HMAC digest that can be used to verify the sender      |
+-------------------+--------------------------------------------------------+
| ``User-Agent``    | User agent string, including Thorn and client version. |
+-------------------+--------------------------------------------------------+
| ``Content-Type``  | Delivery content type (e.g. application/json).         |
+-------------------+--------------------------------------------------------+

HTTPS/SSL Requests
==================

Thorn supports using ``https://`` URLs as callbacks, but for that to work
the destination web server must be properly configured for HTTPS and have
a valid server certificate.
