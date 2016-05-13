"""

    thorn.django.apps
    =================

    Django application configurations.

"""
from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

__all__ = ['WebhooksConfig']


class WebhooksConfig(AppConfig):
    name = 'thorn.django'
    label = 'webhooks'
    verbose_name = _('Webhooks')
