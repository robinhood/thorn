from __future__ import absolute_import, unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$',
        views.ArticleList.as_view(), name='list'),
    url(r'^(?P<id>[0-9a-fA-F-]+)/$',
        views.ArticleDetail.as_view(), name='detail'),
]
