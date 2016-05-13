"""

    thorn.django.rest_framework.views
    =================================

    API endpoints for users to create and manage their webhook subscriptions.

"""
from __future__ import absolute_import, unicode_literals

from rest_framework.generics import (
    ListCreateAPIView, RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated

from django.shortcuts import get_object_or_404

from thorn._state import current_app
from thorn.django.models import Subscriber

from .serializers import SubscriberSerializer

__all__ = ['SubscriberList', 'SubscriberDetail']


def _permission_classes(view):
    perms = current_app().settings.THORN_DRF_PERMISSION_CLASSES
    return perms if perms is not None else (IsAuthenticated,)


class SubscriberList(ListCreateAPIView):
    """List and create new subscriptions for the currently logged in user."""

    serializer_class = SubscriberSerializer
    model = Subscriber
    permission_classes = property(_permission_classes)

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SubscriberDetail(RetrieveUpdateDestroyAPIView):
    """Update, delete or get details for specific subscription owned by
    the currently logged in user."""

    serializer_class = SubscriberSerializer
    model = Subscriber
    lookup_field = 'uuid'
    permission_classes = property(_permission_classes)

    def get_object(self):
        return get_object_or_404(
            self.model, user=self.request.user, uuid=self.kwargs['uuid'],
        )
