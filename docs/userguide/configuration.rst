.. _configuration-guide:

=============================================================================
                              Configuration
=============================================================================

.. contents:: Table of Contents:
    :local:
    :depth: 1

Reference
=========

.. setting:: THORN_CHUNKSIZE

``THORN_CHUNKSIZE``
-------------------

Used by the :pypi:`Celery` dispatcher to decide how many HTTP requests
each task will perform.

Default is 10.

.. setting:: THORN_CODECS

``THORN_CODECS``
----------------

Can be used to configure new webhook serializers, or modify existing
serializers:

.. code-block:: python

    THORN_CODECS = {'application/json': serialize_json}

.. setting:: THORN_SUBSCRIBERS

``THORN_SUBSCRIBERS``
---------------------

This setting enables you to add static event subscribers
that are not stored in the database.

This is useful for e.g hardcoded webhooks between internal systems.

The value of this setting should be a mapping between event names
and subscribers, where subscribers can be:

- a URL or a list of URLs.
- a dict configured subscriber supported by
  :meth:`~thorn.django.models.Subscriber.from_dict`, or a list of these.

Example:

.. code-block:: python

    THORN_SUBSCRIBERS = {
        'user.on_create': 'https://example.com/e/on_user_created',
        'address.on_change': {
            'url': 'https://foo.example.com/e/address_change',
            'content_type': 'application/x-www-form-urlencoded',
        }
        'balance.negative': [
            'http://accounts.example.com/e/on_negative_balance',
            'http://metrics.example.com/e/on_negative_balance',
        ]
    }

The value here can also be a callback function that returns more subscribers:

.. code-block:: python

    # can be generator, or just return list
    def address_change_subscribers(event, sender=None, **kwargs):
        for url in subscribers_for('address.change'):
            yield url

    THORN_SUBSCRIBERS = {
        'address.on_change': [address_change_subscribers],
    }

.. setting:: THORN_DISPATCHER

``THORN_DISPATCHER``
--------------------

The dispatcher backend to use, can be one of the built-in aliases:
`"default"`, `"celery"`, or `"disabled"`,
or it can be the fully qualified path to a dispatcher backend class,
e.g. `"proj.dispatchers:Dispatcher"`.

Default is `"default"`.

.. setting:: THORN_EVENT_CHOICES

``THORN_EVENT_CHOICES``
-----------------------

Optional configuration option to restrict the event destination
choices for the Subscriber model.

.. setting:: THORN_DRF_PERMISSION_CLASSES

``THORN_DRF_PERMISSION_CLASSES``
--------------------------------

List of permission classes to add to the Django Rest Framework views.

.. setting:: THORN_EVENT_TIMEOUT

``THORN_EVENT_TIMEOUT``
-----------------------

HTTP request timeout used as default when dispatching events,
in seconds int/float.

Default is 3.0 seconds.

.. setting:: THORN_RETRY

``THORN_RETRY``
---------------

Enable/disable retry of HTTP requests that times out or returns an error respons.

Enabled by default.

.. setting:: THORN_RETRY_DELAY

``THORN_RETRY_DELAY``
---------------------

Time in seconds (int/float) to wait between retries.  Default is one minute.

.. setting:: THORN_RETRY_MAX

``THORN_RETRY_MAX``
-------------------

Maximum number of retries before giving up.  Default is 10.

Note that subscriptions are currently not cancelled if exceeding the maximum
retry amount.

.. setting:: THORN_RECIPIENT_VALIDATORS

``THORN_RECIPIENT_VALIDATORS``
------------------------------

List of default validator functions to validate recipient URLs.

Individual events can override this using the ``recipient_validators``
argument.

The default set of validators will validate that:

- That the IP address of the recipient is not on a local network.

    .. warning::

        This only applies to IP addresses reserved for internal
        use, such as 127.0.0.1, and 192.168.0.0/16.

        If you have private networks on a public IP address you can
        block them by using the :func:`~thorn.validators.block_cidr_network`
        validator.

- The scheme of the recipient is either HTTP or HTTPS.

- The port of the recipient is either 80, or 443.

This is expressed in configuration as:

.. code-block:: python

    THORN_RECIPIENT_VALIDATORS = [
        validators.block_internal_ips(),
        validators.ensure_protocol('http', 'https'),
        validators.ensure_port(80, 443),
    ]

More validators can be found in the API reference for the
:mod:`thorn.validators` module.
