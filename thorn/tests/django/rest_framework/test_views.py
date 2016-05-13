from __future__ import absolute_import, unicode_literals

from rest_framework.permissions import IsAuthenticated

from thorn.django.rest_framework.views import (
    SubscriberList, SubscriberDetail,
)

from thorn.tests.case import Case, Mock, SkipTest, patch


class ViewCase(Case):
    View = None
    kwargs = {}

    def setUp(self):
        if self.View is None:
            raise SkipTest('abstract test')
        self.view = self.View()
        self.view.request = Mock(name='request')
        self.view.model = Mock(name='model')
        self.view.kwargs = dict(self.kwargs)

    @patch('thorn.django.rest_framework.views.current_app')
    def test_permission_classes(self, current_app):
        app = current_app()
        app.settings.THORN_DRF_PERMISSION_CLASSES = None
        self.assertTupleEqual(self.view.permission_classes, (IsAuthenticated,))
        app.settings.THORN_DRF_PERMISSION_CLASSES = (303, 808)
        self.assertTupleEqual(self.view.permission_classes, (303, 808))


class test_SubdscriberList(ViewCase):
    View = SubscriberList

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        self.view.model.objects.filter.assert_called_with(
            user=self.view.request.user,
        )
        self.assertIs(qs, self.view.model.objects.filter())

    def test_perform_create(self):
        serializer = Mock(name='serializer')
        self.view.perform_create(serializer)
        serializer.save.assert_called_with(user=self.view.request.user)


class test_SubscriberDetail(ViewCase):
    View = SubscriberDetail
    kwargs = {'uuid': 'id#1'}

    @patch('thorn.django.rest_framework.views.get_object_or_404')
    def test_get_object(self, get_object_or_404):
        subscriver = self.view.get_object()
        get_object_or_404.assert_called_with(
            self.view.model, user=self.view.request.user, uuid='id#1',
        )
        self.assertIs(subscriver, get_object_or_404())
