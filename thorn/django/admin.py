"""

    thorn.django.admin
    ==================

    Django-Admin interface support for managing webhook subscriptions.

"""
from __future__ import absolute_import, unicode_literals

from django.contrib import admin

from . import models

admin.site.register(models.Subscriber)
