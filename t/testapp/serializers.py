from __future__ import absolute_import, unicode_literals

from rest_framework import serializers

from .models import Article

__all__ = ['ArticleSerializer']


class ArticleSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(source='id', read_only=True)
    author = serializers.IntegerField(source='author.pk')

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'state', 'author',
        )
        read_only_fields = ('id',)
