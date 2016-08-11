from __future__ import absolute_import, unicode_literals

import pytest

from case import Mock

from rest_framework.permissions import IsAuthenticated

from thorn.django.rest_framework.views import (
    SubscriberList, SubscriberDetail,
)


def mock_view(View, **kwargs):
    view = View()
    view.request = Mock(name='request')
    view.model = Mock(name='model')
    view.kwargs = dict(kwargs)
    return view


class test_SubscriberList:
    View = SubscriberList

    def test_get_queryset(self):
        view = mock_view(self.View)
        qs = view.get_queryset()
        view.model.objects.filter.assert_called_with(
            user=view.request.user,
        )
        assert qs is view.model.objects.filter()

    def test_perform_create(self):
        view = mock_view(self.View)
        serializer = Mock(name='serializer')
        view.perform_create(serializer)
        serializer.save.assert_called_with(user=view.request.user)


class test_SubscriberDetail:
    View = SubscriberDetail

    def test_get_object(self, patching):
        get_object_or_404 = patching(
            'thorn.django.rest_framework.views.get_object_or_404')
        view = mock_view(self.View, uuid='id#1')
        subscriber = view.get_object()
        get_object_or_404.assert_called_with(
            view.model, user=view.request.user, uuid='id#1',
        )
        assert subscriber is get_object_or_404()


@pytest.mark.parametrize('View', [SubscriberList, SubscriberDetail])
def test_permission_classes(patching, View):
    view = mock_view(View)
    current_app = patching(
        'thorn.django.rest_framework.views.current_app')
    app = current_app()
    app.settings.THORN_DRF_PERMISSION_CLASSES = None
    assert view.permission_classes == (IsAuthenticated,)
    app.settings.THORN_DRF_PERMISSION_CLASSES = (303, 808)
    assert view.permission_classes == (303, 808)
