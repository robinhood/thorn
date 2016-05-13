.. image:: http://thorn.readthedocs.io/en/latest/_images/thorn_banner.png

|build-status| |coverage|

:Version: 1.0.0
:Web: http://thorn.readthedocs.io/
:Download: http://pypi.python.org/pypi/thorn/
:Source: http://github.com/robinhood/thorn/
:Keywords: event driven, webhooks, callback, http, django

.. contents:: Table of Contents:
    :local:


About
=====

Thorn is a webhook framework for Python, focusing on flexibility and
ease of use, both when getting started and when maintaining a production
system.

The goal is for webhooks to thrive on the web, by providing Python projects
with an easy solution to implement them and keeping a repository of patterns
evolved by the Python community.

- **Simple**

    Add webhook capabilities to your database models using a single
    decorator, including filtering for specific changes to the model.

- **Flexible**

    All Thorn components are pluggable, reusable and extendable.

- **Scalable**

    Thorn can perform millions of HTTP requests every second by taking
    advantage of `Celery`_ for asynchronous processing.

.. _`Celery`: http://celeryproject.org/

What are webhooks?
==================

A webhook is a fancy name for an HTTP callback.

Users and other services can subscribe to events happening in your system
by registering a URL to be called whenever the event occurs.

The canonical example would be GitHub where you can register URLs to be
called whenever a new change is committed to your repository, a new
bugtracker issue is created, someone publishes a comment, and so on.

Another example is communication between internal systems, traditionally
dominated by complicated message consumer daemons, using webhooks
is an elegant and REST friendly way to implement event driven systems,
requiring only a web-server (and optimally a separate service to dispatch
the HTTP callback requests).

Webhooks are also composable, so you can combine multiple HTTP callbacks
to form complicated workflows, executed as events happen across multiple
systems.

In use
------

Notable examples of webhooks in use are:

+------------+---------------------------------------------------------------+
| **Site**   | **Documentation**                                             |
+------------+---------------------------------------------------------------+
|   Github   | https://developer.github.com/webhooks/                        |
+------------+---------------------------------------------------------------+
|   Stripe   | https://stripe.com/docs/webhooks                              |
+------------+---------------------------------------------------------------+
|   PayPal   | http://bit.ly/1TbDtvj                                         |
+------------+---------------------------------------------------------------+

Example
-------

This example adds four webhook events to the Article model of
an imaginary blog engine:
::

    from thorn import ModelEvent, model_reverser, webhook_model

    @webhook_model(
        on_create=ModelEvent('article.created')
        on_change=ModelEvent('article.changed'),
        on_delete=ModelEvent('article.removed'),
        on_publish=ModelEvent(
            'article.published',
            state__eq='PUBLISHED').dispatches_on_change(),
        reverse=model_reverser('article:detail', uuid='uuid'),
    )
    class Article(models.Model):
        pass  # ...

Users can now subscribe to the four events individually, or all of them
by subscribing to ``article.*``, and will be notified every time
an article is created, changed, removed or published:
::

    $ curl -X POST                                                      \
    > -H "Authorization: Bearer <secret login token>"                   \
    > -H "Content-Type: application/json"                               \
    > -d '{"event": "article.*", "url": "https://e.com/h/article?u=1"}' \
    > http://example.com/hooks/

The API is expressive, so may require you to learn more about the arguments
to understand it fully.  Luckily it's all described in the
`Events Guide`_ for you to consult after reading
the quick start tutorial.

What do I need?
===============

.. sidebar:: Version Requirements
    :subtitle: Thorn version 1.0 runs on

    - Python (2.7, 3.4, 3.5)
    - PyPy (5.1.1)
    - Jython (2.7).

Thorn currently only supports `Django`_, and an API for subscribing to events
is only provided for `Django REST Framework`_.

Extending Thorn is simple so you can also contribute support
for your favorite frameworks.

For dispatching web requests we recommend using `Celery`_, but you
can get started immediately by dispatching requests locally.

Using `Celery`_ for dispatching requests will require a message transport
like `RabbitMQ`_ or `Redis`_.

You can also write custom dispatchers if you have an idea for efficient
payload delivery, or just want to reuse a technology you already deploy in
production.

.. _`Celery`: http://celeryproject.org/
.. _`Django`: http://djangoproject.com/
.. _`Django REST Framework`: http://www.django-rest-framework.org
.. _`RabbitMQ`: http://rabbitmq.com
.. _`Redis`: http://redis.io

Quick Start
===========

Go immediately to the ``django-guide`` guide to get started using
Thorn in your Django projects.

If you are using a different web framework, please consider contributing
to the project by implementing a new environment type.

Alternatives
============

Thorn was inspired by multiple Python projects:

- `dj-webhooks`_
- `django-rest-hooks`_
- `durian`_

.. _`dj-webhooks`: https://github.com/pydanny/dj-webhooks
.. _`django-rest-hooks`: https://github.com/zapier/django-rest-hooks
.. _`durian`: https://github.com/ask/durian/

.. _`Events Guide`: http://thorn.readthedocs.io/en/latest/userguide/events.html

.. _installation:

Installation
============

Installing the stable version
-----------------------------

You can install thorn either via the Python Package Index (PyPI)
or from source.

To install using `pip`:
::

    $ pip install -U thorn

.. _installing-from-source:

Downloading and installing from source
--------------------------------------

Download the latest version of thorn from
http://pypi.python.org/pypi/thorn/

You can install it by doing the following,:
::

    $ tar xvfz thorn-0.0.0.tar.gz
    $ cd thorn-0.0.0
    $ python setup.py build
    # python setup.py install

The last command must be executed as a privileged user if
you are not currently using a virtualenv.

.. _installing-from-git:

Using the development version
-----------------------------

With pip
~~~~~~~~

You can install the latest snapshot of thorn using the following
pip command:
::

    $ pip install https://github.com/robinhood/thorn/zipball/master#egg=thorn

.. _`Events Guide`: http://thorn.readthedocs.io/en/latest/userguide/events.html

.. _getting-help:

Getting Help
============

.. _mailing-list:

Mailing list
------------

For discussions about the usage, development, and future of Thorn,
please join the `thorn-users`_ mailing list.

.. _`thorn-users`: https://groups.google.com/forum/#!forum/thorn-users

.. _irc-channel:

IRC
---

Come chat with us on IRC. The **#thorn** channel is located at the `Freenode`_
network.

.. _`Freenode`: http://freenode.net

.. _bug-tracker:

Bug tracker
===========

If you have any suggestions, bug reports or annoyances please report them
to our issue tracker at https://github.com/robinhood/thorn/issues/

.. _contributing-short:

Contributing
============

Development of `Thorn` happens at GitHub: https://github.com/robinhood/thorn

You are highly encouraged to participate in the development
of `thorn`. If you don't like GitHub (for some reason) you're welcome
to send regular patches.

Be sure to also read the `Contributing to Thorn`_ section in the
documentation.

.. _`Contributing to Thorn`:
    http://thorn.readthedocs.io/en/latest.html

.. _license:

License
=======

This software is licensed under the `New BSD License`. See the ``LICENSE``
file in the top distribution directory for the full license text.

.. # vim: syntax=rst expandtab tabstop=4 shiftwidth=4 shiftround

.. _`Events Guide`: http://thorn.readthedocs.io/en/latest/userguide/events.html

.. |build-status| image:: https://secure.travis-ci.org/robinhood/thorn.png?branch=master
    :alt: Build status
    :target: https://travis-ci.org/robinhood/thorn

.. |coverage| image:: https://codecov.io/github/robinhood/thorn/coverage.svg?branch=master
    :target: https://codecov.io/github/robinhood/thorn?branch=master

.. _`Events Guide`: http://thorn.readthedocs.io/en/latest/userguide/events.html

