.. _optimization-guide:

=============================================================================
                        Optimization and Performance
=============================================================================

.. contents:: Table of Contents:
    :local:
    :depth: 1

Celery
======

Eventlet/Gevent
---------------

By far the best way to deploy Thorn for optimal web request performance
is to use the Celery eventlet/gevent pools.  Which one you choose does not
matter much, but some will prefer one over the other.

To start a Celery worker with the eventlet/gevent pool set the
:option:`-P <celery worker -P>` option:

.. code-block:: console

    $ celery -A proj worker -l info -P eventlet -c 1000

The :option:`-c 1000 <celery worker -c>` tells the worker to use up to one
thousand green-threads for task execution.

Note that this will only start one OS process, so to take advantage of
multiple CPUs or CPU-cores you need to start multiple processes.

This can be achived by using the :envvar:`CELERYD_NODES` option to the Celery
generic-init.d script, or by manually starting :program:`celery multi`,
for example if you have four CPU-cores you may want to start four worker
instances, with a thousand green-threads each:

.. code-block:: console

    $ celery multi start 4 -A proj -P eventlet -c 1000
    $ celery multi restart 4 -A proj -P eventlet -c 1000
    $ celery multi stop 4 -A proj -P eventlet -c 1000

Eventlet: Asynchronous DNS lookups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To use the Celery eventlet pool you should make sure to install the
:pypi:`dnspython` library, to enable asynchronous DNS lookups:

.. code-block:: console

    $ pip install dnspython

Task retry settings
~~~~~~~~~~~~~~~~~~~

Prefetch multiplier
-------------------
