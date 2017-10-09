.. _subscribers-guide:

=============================================================================
                               Subscribers
=============================================================================

.. contents:: Table of Contents:
    :local:
    :depth: 1

Introduction
============

Interested parties can subscribe to webhook events by registering
a :class:`~thorn.django.models.Subscriber`.

Subscribers are stored in the database.

The subscription can match an event by simple pattern matching,
and also filter by events related to a specific user (requires
the event to be sent with a ``sender`` argument).

A simple subscriber can be created from the repl,
like in this example where all ``article.`` related events
will be sent to the URL: http://example.com/receive/article,
and the payload is requested to be in *json* format:

.. code-block:: pycon

    >>> Subscriber.objects.create(
            event='article.*',
            url='http://example.com/receive/article',
            content_type='application/json',
    ... )

Sending events to only a subset of subscribers
----------------------------------------------
Thorn can send an event either to all subscribers or to the single subscriber
whose :attr:`~thorn.generic.models.AbstractSubscriber.user` attribute matches
the ``sender`` keyword argument passed to :meth:`~thorn.events.Event.send`.
