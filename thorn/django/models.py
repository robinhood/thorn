"""

    thorn.django.models
    ===================

    Django models required to dispatch webhook events.

"""
from __future__ import absolute_import, unicode_literals

from uuid import uuid4

from django.conf import settings as django_settings
from django.db import models
from django.utils import text
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from thorn.conf import event_choices, MIME_JSON, MIME_URLFORM
from thorn.models import SubscriberModelMixin

from .managers import SubscriberManager

__all__ = ['Subscriber']

#: max size when indexing InnoDB utf8mb4
#: reportedly this is caused by MySQL being purposefully and irreversibly
#: brain-damaged: https://code.djangoproject.com/ticket/18392
CHAR_MAX_LENGTH = 190

CONTENT_TYPES = {
    MIME_JSON,
    MIME_URLFORM,
}


@python_2_unicode_compatible
class Subscriber(models.Model, SubscriberModelMixin):
    user_id_field = 'pk'

    objects = SubscriberManager()

    uuid = models.UUIDField(
        _('UUID'),
        default=uuid4, editable=False, unique=True, null=False,
        help_text=_('Unique identifier for this subscriber.')
    )

    event = models.CharField(
        _('event'),
        max_length=CHAR_MAX_LENGTH,
        choices=event_choices(),
        db_index=True,
        help_text=_('Name of event to connect with'),
    )

    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        related_name='%(app_label)s_%(class)s',
        null=True,
    )

    url = models.URLField(
        _('URL'),
        max_length=CHAR_MAX_LENGTH,
        db_index=True,
        help_text=_('Callback URL'),
    )

    content_type = models.CharField(
        _('content type'),
        max_length=CHAR_MAX_LENGTH,
        choices=zip(CONTENT_TYPES, CONTENT_TYPES),
        default=MIME_JSON,
        help_text='Desired content type for requests to this callback.'
    )

    created_at = models.DateTimeField(
        _('created at'), editable=False, auto_now_add=True)

    updated_at = models.DateTimeField(
        _('updated_at'), editable=False, auto_now=True,
    )

    class Meta:
        verbose_name = _('subscriber')
        verbose_name_plural = _('subscriber')
        # ordering by hostname for ability to optimize for keepalive.
        ordering = ['url', '-created_at']
        get_latest_by = 'updated_at'
        unique_together = ('url', 'event')

    def __str__(self):
        return '{0} -> {1}'.format(
            self.event, text.Truncator(self.url).chars(43),
        )
