.. _glossary:

Glossary
========

.. glossary::
    :sorted:

    subscriber
        An URL subscribing to a webhook.

    subscription
        The actual subscription that can be cancelled.  Identified
        by a universally unique identifier (UUID4).

    dispatch
        The act of notifying all subscriptions subscribed to a webhook,
        by performing one or more HTTP requests.

    webhook
        An HTTP callback.

    celery
        A distributed task queue library (http://celeryproject.org).
