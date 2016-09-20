"""Tools for URL references."""
from __future__ import absolute_import, unicode_literals

from operator import attrgetter
from six import iteritems as items

from thorn._state import app_or_default

__all__ = ['model_reverser']


class model_reverser(object):
    """Describes how to get the canonical URL for a model instance.

    Examples:
        >>> # This:
        >>> model_reverser('article-detail', uuid='uuid')
        >>> # for an article instance will generate the URL by calling:
        >>> reverse('article_detail', kwargs={'uuid': instance.uuid})

        >>> # And this:
        >>> model_reverser('article-detail', 'category.name', uuid='uuid')
        >>> # for an article instance will generate the URL by calling:
        >>> reverse('article-detail',
        ...         args=[instance.category.name],
        ...         kwargs={'uuid': instance.uuid},
        ... )
    """

    def __init__(self, view_name, *args, **kwargs):
        # type: (str, *Any, **Any) -> None
        self.view_name = view_name
        self.args = args
        self.kwargs = kwargs

    def __call__(self, instance, app=None, **kw):
        # type: (Model, App, **Any) -> str
        return app_or_default(app).reverse(
            self.view_name,
            args=[attrgetter(arg)(instance) for arg in self.args],
            kwargs={
                key: attrgetter(value)(instance)
                for key, value in items(self.kwargs)
            },
            **kw
        )
