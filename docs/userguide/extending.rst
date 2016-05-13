.. _extending-guide:

=============================================================================
                                Extending
=============================================================================

.. contents:: Table of Contents:
    :local:
    :depth: 1

.. _extending-environment:

Environment
===========

The environment holds framework integration specific features,
and will point to a suitable implementation of the subscriber
model, database signals, and the function used for reverse URL lookups.

Currently only Django is supported using the
:class:`thorn.environment.django.DjangoEnv` environment.

If you want to contribute an integration for another framework you
can use this environment as a template for your implementation.

Autodetection
-------------

An environment is selected by calling the ``autodetect()`` class method
on all registered environments.

The first environment to return a true value will be selected.

As an example, the Django-environment is selected only
if the :envvar:`DJANGO_SETTINGS_MODULE` is set.
