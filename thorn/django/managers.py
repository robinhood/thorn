"""

    thorn.django.managers
    =====================

    Managers and query sets.

"""
from __future__ import absolute_import, unicode_literals

from django.db import models
from django.db.models.query import Q

__all__ = ['SubscriberQuerySet', 'SubscriberManager']


class SubscriberQuerySet(models.QuerySet):

    def matching(self, event, user=None):
        return self.matching_event(event).matching_user_or_all(user)

    def matching_event(self, event):
        topic, _, rest = event.partition('.')
        # order.completed
        # order.*
        # *.completed
        return self.filter(
            Q(event__exact=event) |
            Q(event__exact='{0}.*'.format(topic)) |
            Q(event__exact='*.{0}'.format(rest))
        )

    def matching_user_or_all(self, user):
        return self.filter(user=user) if user else self


class SubscriberManager(models.Manager.from_queryset(SubscriberQuerySet)):
    pass
