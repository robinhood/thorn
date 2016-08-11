from __future__ import absolute_import, unicode_literals

from rest_framework.generics import (
    ListCreateAPIView, RetrieveUpdateDestroyAPIView,
)
from django.shortcuts import get_object_or_404

from .models import Article
from .serializers import ArticleSerializer

__all__ = ['ArticleList', 'ArticleDetail']


class ArticleList(ListCreateAPIView):
    serializer_class = ArticleSerializer
    model = Article

    def get_queryset(self):
        return self.model.objects.all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ArticleDetail(RetrieveUpdateDestroyAPIView):
    serializer_class = ArticleSerializer
    model = Article
    lookup_field = 'id'

    def get_object(self):
        return get_object_or_404(
            self.model, id=self.kwargs['id'],
        )
