.. _events-guide:

=============================================================================
                                Events
=============================================================================

.. contents:: Table of Contents:
    :local:
    :depth: 2

Introduction
============

An event can be anything happening in your system that something external
wants to be notified about.

The most basic type of event is the :class:`~thorn.events.Event` class,
from which other more complicated types of events can be built.  The basic
event does not have any protocol specification, so any payload is
accepted.

An :class:`~thorn.events.Event` is decoupled from subscribers and dispatchers and
simply describes an event that can be subscribed to and dispatched to subscribers.

In this guide we will first be describing the basic event building
blocks, so that you understand how they work, then move on to the API
you are most likely to be using: the ``ModelEvent`` class and ``@webhook_model``
decorator used to associate events with database models.

.. _events-basics-defining:

Defining events
---------------

Say you would like to define an event that dispatches whenever
a new user is created, you can do so by creating a new
:class:`~thorn.events.Event` object, giving it a name and assigning
it to a variable:

.. code-block:: python

    from thorn import Event

    on_user_created = Event('user.created')

Currently this event is merely defined, and won't be dispatched under any
circumstance unless you manually do so by calling ``on_user_created.send()``.

Since the event name is ``user.created`` it's easy to imagine this being
sent from something like a web view responsible for creating users,
or whenever a user model is changed.

Naming events
-------------

Subscribers can filter events by simple pattern matching, so event names should
normally be composed out of a category name and an event name, separated by
a single dot:

.. code-block:: text

    "category.name"

A subscription to ``"user.*"`` will match events ``"user.created"``,
``"user.changed"``, and ``"user.removed"``; while a subscription to
``"*.created"`` will match ``"user.created"``, ``"article.created"``, and so
on.

.. _events-basics-sending:

Sending events
--------------

.. code-block:: python

    from userapp import events
    from userapp.models import User


    def create_user(request):
        username = request.POST['username']
        password = request.POST['password']
        user = User.objects.create(username=username, password=password)
        events.on_user_created.send({
            'uuid': user.uuid,
            'username': user.username,
            'url': 'http://mysite/users/{0}/'.format(user.uuid),
        })

.. _events-basics-timeouts:

Timeouts and retries
--------------------

Dispatching an event will ultimately mean performing one or more HTTP requests
if there are subscribers attached to that event.

Many HTTP requests will be quick, but some of them will be problematic,
especially if you let arbitrary users register external URL callbacks.

A web server taking too long to respond can be handled by setting a socket
timeout such that an error is raised.  This timeout error can be combined
with retries to retry at a later time when the web server is hopefully under
less strain.

Slow HTTP requests is usually fine when using the Celery dispatcher,
merely blocking that process/thread from doing other work,
but when dispatching directly from a web server process it can be
deadly, especially if the timeout settings are not tuned properly.

The default timeout for web requests related to an event is configured by the
:setting:`THORN_EVENT_TIMEOUT` setting, and is set to 3 seconds by default.

Individual events can override the default timeout by providing
either a ``timeout`` argument when creating the event:

.. code-block:: pycon

    >>> on_user_created = Event('user.created', timeout=10.0)

or as an argument to the :meth:`~thorn.events.Event.send` method:

.. code-block:: pycon

    >>> on_user_created.send(timeout=1.5)

In addition to the web server being slow to respond, there are other intermittent
problems that can occur, such as a 500 (Internal Server Error) response, or
even a 404 (Resource Not Found).

The right way to deal with these errors is to retry performing the HTTP
request at a later time and this is configured by the event retry policy settings:

.. code-block:: python

    >>> on_user_created = Event(
    ...     'user.created',
    ...     retry=True,
    ...     retry_max=10,
    ...     retry_delay=60.0,
    ... )

The values used here also happen to be the default setting, and can be
configured for all events using the :setting:`THORN_RETRY`,
:setting:`THORN_RETRY_MAX` and :setting:`THORN_RETRY_DELAY` settings.

.. _events-serialization:

Serialization
-------------

Events are always serialized using the `json`_ serialization format [*]_,
which means the data you provide in the webhook payload must be representable
in *json* or an error will be raised.

The built-in data types supported by *json* are:

- ``int``
- ``float``
- ``string``
- ``dictionary``
- ``list``

In addition Thorn adds the capability to serialize the following Python types:

- :class:`datetime.datetime`: converted to `ISO-8601`_ string.

- :class:`datetime.date`: converted to `ISO-8601`_ string.

- :class:`datetime.time`: converted to `ISO-8601`_ string.

- :class:`decimal.Decimal`:
    converted to string as the *json* float type is unreliable.

- :class:`uuid.UUID`: converted to string.

- :class:`django.utils.functional.Promise`:
    if :pypi:`django` is installed, converted to string.

.. _`json`: http://www.json.org
.. _`ISO-8601`: https://en.wikipedia.org/wiki/ISO_8601

.. _events-model:

Model events
============

In most cases your events will actually be related to a database model being
created, changed, or deleted, which is why Thorn comes with a convenience event
type just for this purpose, and even a decorator to easily add
webhook-capabilities to your database models.

This is the :class:`thorn.ModelEvent` event type, and the
:class:`@webhook_model() <thorn.webhook_model>` decorator.

We will be giving an example in a moment, but first we will discuss the
message format for model events.

.. _events-model-message-format:

Message format
--------------

The model events have a standard message format specification, which is really
more of a header with arbitrary data attached.

An example model event message serialized by `json`_ would look like this:

.. code-block:: json

    {"event": "(str)event_name",
     "ref": "(URL)model_location",
     "sender": "(User pk)optional_sender",
     "data": {"event specific data": "value"}}

The most important part here is ``ref``, which is optional
but lets you link back to the resource affected by the event.

We will discuss reversing models to provide the ``ref`` later in this chapter.

.. _events-model-decorator:

Decorating models
-----------------

The easiest way to add webhook-capabilities to your models is by using
the :class:`@webhook_model() <thorn.webhook>` decorator.

Here's an example decorating a Django ORM model:

.. code-block:: python

    from django.db import models

    from thorn import ModelEvent, model_reverser, webhook_model


    @webhook_model(
        on_create=ModelEvent('article.created'),
        on_change=ModelEvent('article.changed'),
        on_delete=ModelEvent('article.removed'),
        on_publish=ModelEvent(
            'article.published', state__now_eq='PUBLISHED',
        ).dispatches_on_change(),
        reverse=model_reverser('article:detail', uuid='uuid'),
    )
    class Article(models.Model):
        uuid = models.UUIDField()
        title = models.CharField(max_length=128)
        state = models.CharField(max_length=128, default='PENDING')
        body = models.TextField()

        def webhook_payload(self):
            return {
                'title': self.title,
            }

.. admonition:: Why is this example using Django?

    Rest assured that Thorn is not a Django-specific library
    and should be flexible enough to integrate with any framework,
    but we have to use something for these generic examples,
    and Django is the only framework currently supported.

    Please get in touch if you want to add support for additional
    frameworks, it's not as tricky as it sounds and we can help!


The arguments to this decorator is probably a bit confusing at first,
but how expressive this interface is will be apparent once you learn more
about them.

So let's discuss the decorator arguments one by one:

#. ``on_create=ModelEvent('article.created')``

    Here we specify an event to be sent every time a new object of this
    model type is created.

    The webhook model decorator can accept an arbitrary number of custom
    events, but there are three types of events the decorator already knows how to
    dispatch: ``on_create``, ``on_change`` and ``on_delete``.  For any additional
    events you are required to specify the dispatch mechanism (see later
    explanation of the ``on_publish`` argument).

    The name ``"article.created"`` here is the event name that subscribers can
    use to subscribe to this event.

#. ``on_change=ModelEvent('article.changed')``

    Just like ``on_create`` and ``on_delete`` the decorator does not need
    to know when an ``on_change`` event is to be dispatched: it will be sent
    whenever an object of this model type is changed.

#. ``on_delete=ModelEvent('article.deleted')``

    I'm sure you can guess what this one does already! This event will
    be sent whenever an object of this model type is deleted.

#. ``on_publish=ModelEvent('article.published', state__now_eq='PUBLISHED')``

    Here we define a custom event type with an active filter.

    The filter (``state__now_eq='PUBLISHED'``) in combination with the specified
    dispatch type (``.dispatched_on_change``) means the event will only be
    sent when 1) an Article is changed and 2) the updated state changed
    from something else to ``"PUBLISHED"``.

    The decorator will happily accept any argument starting with ``on_``
    as an event associated with this model, and any argument to
    :class:`~thorn.ModelEvent` ending with ``__eq``, ``__ne``, ``__gt``,
    ``__gte``, ``__lt``, ``__lte``,  ``__is``, ``__is_not``, ``__contains``,
    ``__startswith`` or ``__endswith`` will be regarded as a filter argument.

    You can even use ``Q`` objects to create elaborate boolean structures,
    which is described in detail in the :ref:`events-model-filtering`
    section.

#. ``reverse=model_reverser('article.detail', uuid='uuid')``

    This tells the decorator how to get the canonical URL of an object of
    this model type, which is used as the ``ref`` field in the webhook
    :ref:`message payload <events-model-message-format>`.

    In this case the reverser, when using Django, will translate directly
    into:

    .. code-block:: pycon

        >>> from django.core.urlresolvers import reverse
        >>> reverse('article.detail', kwargs={'uuid': instance.uuid})
        http://example.com/article/3d90c42c-d61e-4579-ab8f-733d955529ad/

    See :ref:`events-model-reverse` for more examples of model reversers.

.. admonition:: Django signals and bulk updates

    A limitation with database signals in Django is that signals are not
    dispatched for bulk operations (``objects.delete()``/
    ``objects.update()``), so you need to dispatch events manually when
    you use this functionality.


.. _events-model-event:

``ModelEvent objects``
======================

This section describes the :class:`~thorn.ModelEvent` objects used
with the :class:`@webhook_model() <thorn.webhook_model>` decorator
in greater detail.

.. _events-model-signals:

Signal dispatch
---------------

A model event will usually be dispatched in reaction to a signal [*]_,
on Django this means connecting to the
:data:`~django.db.models.signals.post_save` and
:data:`~django.db.models.signals.post_delete` signals.

There are three built-in signal dispatch handlers:

#. Send when a new model object is created:

    .. code-block:: pycon

        >>> ModelEvent('...').dispatches_on_create()

#. Send when an existing model object is changed:

    .. code-block:: pycon

        >>> ModelEvent('...').dispatches_on_change()

#. Send when an existing model object is deleted:

    .. code-block:: pycon

        >>> ModelEvent('...').dispatches_on_delete()

#. Send when a many-to-many relation is added

    .. code-block:: pycon

        >>> ModelEvent('...').dispatches_on_m2m_add('tags')

    Argument is the related field name, and in this example
    tags is defined on the model as ``tags = ManyToManyField(Tag)``.
    The event will dispatch whenever ``Model.tags.add(related_object)``
    happens.

#. Send when a many-to-many relation is removed

    .. code-block:: pycon

        >>> ModelEvent('...').dispatches_on_m2m_remove('tags')

    Argument is the related field name, and in this example
    tags is defined on the model as ``tags = ManyToManyField(Tag)``.
    The event will dispatch whenever ``Model.tags.remove(related_object)``
    happens.

#. Send when a many-to-many field is cleared

    .. code-block:: pycon

        >>> ModelEvent('...').dispatches_on_m2m_clear('tags')

    Argument is the related field name, and in this example
    tags is defined on the model as ``tags = ManyToManyField(Tag)``.
    The event will dispatch whenever ``Model.tags.clear()``
    happens.

All of these will only be sent when the transaction is committed, or by other
means the changes are final in the database.

The webhook model decorator treats the ``on_create``, ``on_change``, and
``on_delete`` arguments specially so that you don't have to specify
the dispatch mechanism for these, but that is not true for any custom
events you specify by using the ``on_`` argument prefix to
:class:`~thorn.webhook_model`.

.. _events-model-payload:

Modifying event payloads
------------------------

The ``data`` field part of the resulting
:ref:`model event message <events-model-message-format>` will be empty
by default, but you can define a special method on your model class
to populate this with data relevant for the event.

This callback must be named ``webhook_payload``, takes no arguments,
and can return anything as long as it's json-serializable:

.. code-block:: python

    class Article(models.Model):
        uuid = models.UUIDField()
        title = models.CharField(max_length=128)
        state = models.CharField(max_length=128, default='PENDING')
        body = models.TextField()

        def webhook_payload(self):
            return {
                'title': self.title,
                'state': self.state,
                'body': self.body[:1024],
            }

You should carefully consider what you include in the payload to make sure
your messages are as small and lean as possible, so in this case we truncate
the body of the article to save space.

.. tip::

    Do we have to include the article body at all?

    Remember that the webhook message will include the ``ref`` field
    containing a URL pointing back to the affected resource,
    so the recipient can request the full contents of the article
    if they want to.

    Including the body will be a question of how many of your subscribers
    will require the full article text.  If the majority of them will, including
    the body will save them from having to perform an extra HTTP request, but if
    not, you have drastically increased the size of your messages.

.. _events-model-senders:

Event senders
-------------

If your model is associated with a user and you want subscribers
to filter based on the owner/author/etc. of the model instance,
you can include the ``sender_field`` argument:

.. code-block:: python

    from django.contrib.auth import get_user_model
    from django.db import models


    @webhook_model(
        sender_field='author.account.user',
    )
    class Article(models.Model):
        author = models.ForeignKey(Author)


    class Author(models.Model):
        account = models.ForeignKey(Account)


    class Account(models.Model):
        user = models.ForeignKey(get_user_model())

.. _events-model-reverse:

URL references
--------------

To be able to provide a URL reference back to your model object
the event needs to know how to call :func:`django.core.urlresolvers.reverse`
(or equivalent in your web framework) and what arguments to use.

This is where the :class:`~thorn.model_reverser` helper comes in,
which simply describes how to turn an instance of your model into the
arguments used for *reverse*.

The signature of :class:`~thorn.model_reverser` is::

    model_reverser(view_name, *reverse_args, **reverse_kwargs)

The positional arguments will be the names of attributes to take from the
model instance, and the same for keyword arguments.

So if we imagine that the REST API view of our article app is included
like this::

   url(r'^article/', include(
       'apps.article.urls', namespace='article'))

and the URL routing table of the Article app looks like this::

    urlpatterns = [
        url(r'^$',
            views.ArticleList.as_view(), name='list'),
        url(r'^(?P<uuid>[0-9a-fA-F-]+)/$',
            views.ArticleDetail.as_view(), name='detail'),
    ]

We can see that to get the URL of a specific article we need
1) the name of the view (``article:detail``), and
2) a named *uuid* keyword argument:

.. code-block:: python

    >>> from django.core.urlresolvers import reverse
    >>> article = Article.objects.get(uuid='f3f2b22b-8630-412a-a320-5b2644ed723a')
    >>> reverse('article:detail', kwargs={'uuid': article.uuid})
    http://example.com/article/f3f2b22b-8630-412a-a320-5b2644ed723a/

So to define a reverser for this model we can use::

    model_reverser('article:detail', uuid='uuid')

The ``uuid='uuid'`` here means take the ``uuid`` argument from the
identically named field on the instance (``article.uuid``).

Any attribute name is accepted as a value, and even nested attributes
are supported::

    model_reverser('broker:position',
                   account='user.profile.account')
    #               ^^ will be taken from instance.user.profile.account


.. _events-model-filtering:

Filtering
---------

Model events can filter models by matching attributes on the model instance.

The most simple filter would be to match a single field only:

.. code-block:: python

    ModelEvent('article.changed', state__eq='PUBLISHED')

and this will basically transform into the predicate:

.. code-block:: python

    if instance.state == 'PUBLISHED':
        send_event(instance)

This may not be what you want since it will always match even if the
value was already set to ``"PUBLISHED"`` before.   To only match
on the transition from some other value to ``"PUBLISHED"`` you can use
``now_eq`` instead:

.. code-block:: python

    ModelEvent('article.changed', state__now_eq='PUBLISHED')

which will transform into the predicate:

.. code-block:: python

    if (old_value(instance, 'state') != 'PUBLISHED' and
            instance.state == 'PUBLISHED'):
        send_event(instance)

.. admonition:: Transitions and performance

    Using the ``now_*`` operators means Thorn will have to
    fetch the old object from the database before the new version is saved,
    so an extra database hit is required every time you save an instance
    of that model.

You can combine as many filters as you want:

.. code-block:: python

    ModelEvent('article.changed',
               state__eq='PUBLISHED',
               title__startswith('The'))


In this case the filters form an **AND** relationship and will only continue
if all of the filters match:

.. code-block:: python

    if instance.state == 'PUBLISHED' and instance.title.startswith('The'):
        send_event(instance)


If you want an ``OR`` relationship or to combine boolean gates, you will
have to use :class:`~thorn.Q` objects:

.. code-block:: python

    from thorn import ModelEvent, Q


    ModelEvent(
        'article.changed',
        Q(state__eq='PUBLISHED') | Q(state__eq='PREVIEW'),
    )


You can also negate filters using the ``~`` operator:

.. code-block:: python

    ModelEvent(
        'article.changed',
        (
            Q(state__eq='PUBLISHED') |
            Q(state__eq='PREVIEW') &
            ~Q(title__startswith('The'))
        )
    )


Which as our final example will translate into the following pseudo-code:

.. code-block:: python

    if (not instance.title.startswith('The') and
            (instance.state == 'PUBLISHED' or instance.state == 'PREVIEW')):
        send_event(instance)


.. tip::

    Thorn will happily accept Django's :class:`~django.db.query.Q` objects,
    so you don't have to import Q from Thorn when you already have one from
    Django.


Note that you are always required to specify ``__eq`` when specifying filters:

.. code-block:: python

    ModelEvent('article.created', state='PUBLISHED')      # <--- DOES NOT WORK

    ModelEvent('article.created', state__eq='PUBLISHED')  # <-- OK! :o)


.. _events-model-filtering-operators:

Supported operators
~~~~~~~~~~~~~~~~~~~

+----------------------+-----------------------------------------------------------+
| **Operator**         | **Description**                                           |
+----------------------+-----------------------------------------------------------+
| ``eq=B``             | value equal to B (``__eq=True`` tests for truth)          |
+----------------------+-----------------------------------------------------------+
| ``now_eq=B``         | value equal to B and was previously not equal to B        |
+----------------------+-----------------------------------------------------------+
| ``ne=B``             | value not equal to B (``__eq=False`` tests for falsiness) |
+----------------------+-----------------------------------------------------------+
| ``now_ne=B``         | value now not equal to B, but was previously equal to B   |
+----------------------+-----------------------------------------------------------+
| ``gt=B``             | value is greater than B: ``A > B``                        |
+----------------------+-----------------------------------------------------------+
| ``now_gt=B``         | value is greater than B, but was previously less than B   |
+----------------------+-----------------------------------------------------------+
| ``gte=B``            | value is greater than or equal to B: ``A >= B``           |
+----------------------+-----------------------------------------------------------+
| ``now_gte=B``        | value greater or equal to B, previously less or equal     |
+----------------------+-----------------------------------------------------------+
| ``lt=B``             | value is less than B: ``A < B``                           |
+----------------------+-----------------------------------------------------------+
| ``now_lt=B``         | value is less than B, previously greater than B           |
+----------------------+-----------------------------------------------------------+
| ``lte=B``            | value is less than or equal to B: ``A <= B``              |
+----------------------+-----------------------------------------------------------+
| ``now_lte=B``        | value less or equal to B, previously greater or equal.    |
+----------------------+-----------------------------------------------------------+
| ``is=B``             | test for object identity: ``A is B``                      |
+----------------------+-----------------------------------------------------------+
| ``now_is=B``         | value is now identical, but was not previously            |
+----------------------+-----------------------------------------------------------+
| ``is_not=B``         | negated object identity: ``A is not B``                   |
+----------------------+-----------------------------------------------------------+
| ``now_is_not=B``     | value is no longer identical, but was previously          |
+----------------------+-----------------------------------------------------------+
| ``in={B, …}``        | value is a member of set: ``A in {B, …}``                 |
+----------------------+-----------------------------------------------------------+
| ``now_in={B, …}``    | value is now member of set, but was not before            |
+----------------------+-----------------------------------------------------------+
| ``not_in={B, …}``    | value is not a member of set: ``A not in {B, …}``         |
+----------------------+-----------------------------------------------------------+
| ``now_not_in={B, …}``| value is not a member of set, but was before              |
+----------------------+-----------------------------------------------------------+
| ``contains=B``       |  value contains element B: ``B in A``                     |
+----------------------+-----------------------------------------------------------+
| ``now_contains=B``   | value now contains element B, but did not previously      |
+----------------------+-----------------------------------------------------------+
| ``startswith=B``     | string starts with substring B                            |
+----------------------+-----------------------------------------------------------+
| ``now_startswith=B`` | string now startswith B, but did not previously           |
+----------------------+-----------------------------------------------------------+
| ``endswith=B``       | string ends with substring B                              |
+----------------------+-----------------------------------------------------------+
| ``now_endswith=B``   | string now ends with B, but did not previously            |
+----------------------+-----------------------------------------------------------+

Tips
~~~~

- Test for truth/falsiness

    There are two special cases for the ``eq`` operator: ``__eq=True`` and
    ``_eq=False`` is functionally equivalent to ``if A`` and ``if not A``
    so any true-ish or false-ish value will be a match.

    Similarly with ``ne`` the cases ``__ne=True`` and ``__ne=False`` are special
    and translates to ``if not A`` and ``if A`` respectively.

- Use ``A__is=None`` for testing that ``A is None``

- ``contains`` is not limited to strings!

    This operator supports any object supporting the ``__contains__`` protocol
    so in addition to strings it can also be used for sets, lists, tuples,
    dictionaries and other containers.  E.g.: ``B in {1, 2, 3, 4}``.

- The transition operators (``__now_*``) may affect Django database performance.

    Django signals does provide a way to get the previous value of a database
    row when saving an object, so Thorn is required to manually re-fetch the
    object from the database shortly before the object is saved.

Sending model events manually
-----------------------------

The webhook model decorator will add a new ``webhook_events`` attribute
to your model that can be used to access the individual model events:

.. code-block:: pycon

    >>> on_create = Article.webhook_events.events['on_create']

With this you can send the event manually just like any other
:class:`~thorn.Event`:

.. code-block:: pycon

    >>> on_create.send(instance=article, data=article.webhook_payload())

There's also ``.send_from_instance`` which just takes a model instance as
argument and will send the event as if a signal was triggered:

.. code-block:: pycon

    >>> on_create.send_from_instance(instance)

The payload will then look like:

.. code-block:: json

    {
        "event": "article.created",
        "ref": "http://example.com/article/5b841406-60d6-4ca0-b45e-72a9847391fb/",
        "sender": null,
        "data": {"title": "The Mighty Bear"},
    }

.. rubric:: Footnotes

.. [*] Thorn can easily be extended to support additional serialization
       formats.  If this is something you would like to work on then
       please create an issue on the `Github issue tracker`_ or
       otherwise get in touch with the project.

.. [*] By signals we mean an implementation of the `Observer Pattern`_,
       such as :class:`django.dispatch.Signal`,
       :class:`celery.utils.dispatch.Signal`, or :pypi:`blinker` (used by
       Flask).

.. _`Github issue tracker`: https://github.com/robinhood/thorn/issues/
.. _`Observer Pattern`: https://en.wikipedia.org/wiki/Observer_pattern


Security
========

The REST Hooks project has an excellent guide on security and webhooks
here: http://resthooks.org/docs/security/
