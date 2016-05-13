"""

    thorn.webhook.decorators
    ========================

    Webhook decorators.

"""
from __future__ import absolute_import, unicode_literals

from itertools import chain

from six import iteritems as items, itervalues as values


class webhook_model(object):
    """Decorates models to send webhooks based changes to that model.

    :keyword on_create: Event to dispatch whenever an instance of
        this model is created (``post_save``).
    :keyword on_change: Event to dispatch whenever an instance of
        this model is changed (``post_save``).
    :keyword on_delete: Event to dispatch whenever an instance of
        this model is deleted (``post_delete``).
    :keyword on_$event: Additional user defined events.,
    :keyword sender_field:
        Default field used as a sender for events, e.g. ``"account.user"``,
        will use ``instance.account.user``.

        Individual events can override the sender field user.
    :keyword reverse:
        A :class:`thorn.reverse.model_reverser` instance (or any callable
        taking an model instance as argument), that describes how to get
        the URL for an instance of this model.

        Individual events can override the reverser used.

    **Examples**

    Simple article model, where the URL reference is retrieved
    by ``reverse('article-detail', kwargs={'uuid': article.uuid})``:

    .. code-block:: python

        @webhook_model(
            on_create=ModelEvent('article.created'),
            on_change=ModelEvent('article.changed'),
            on_delete=ModelEvent('article.removed'),
            on_deactivate=ModelEvent(
                'article.deactivate', deactivated__eq=True,
            )
            reverse=model_reverser('article-detail', uuid='uuid'),
        )
        class Article(models.Model):
            uuid = models.UUIDField()

    The URL may not actually exist after deletion, so maybe we want
    to point the reference to something else in that special case,
    like a category that can be reversed by doing
    ``reverse('category-detail', args=[article.category.name])``.

    We can do that by having the ``on_delete`` event override
    the reverser used for that event only:

    .. code-block:: python

        @webhook_model(
            on_create=ModelEvent('article.created'),
            on_change=ModelEvent('article.changed'),
            on_delete=ModelEvent(
                'article.removed',
                reverse=model_reverser('category-detail', 'category.name'),
            ),

            on_hipri_delete=ModelEvent(
                'article.internal_delete', priority__gte=30.0,
            ).dispatches_on_delete(),

            reverse=model_reverser('article-detail', uuid='uuid'),
        )
        class Article(model.Model):
            uuid = models.UUIDField()
            category = models.ForeignKey('category')

    """

    def __init__(self,
                 on_create=None, on_change=None, on_delete=None,
                 reverse=None, sender_field=None, **kwargs):
        self.reverse = reverse
        self.sender_field = sender_field
        self.events = {}

        self.update_events(
            {k: v for k, v in items(kwargs) if k.startswith('on_')},
            on_create=on_create and on_create.dispatches_on_create(),
            on_change=on_change and on_change.dispatches_on_change(),
            on_delete=on_delete and on_delete.dispatches_on_delete(),
        )

    def update_events(self, events, **kwargs):
        self.events.update(self.connect_events(events, **kwargs))

    def connect_events(self, events, **kwargs):
        return {
            k: self.contribute_to_event(v)
            for k, v in chain(items(events), items(kwargs))
        }

    def contribute_to_event(self, event):
        if event:
            if event.reverse is None:
                event.reverse = self.reverse
            event.sender_field = self.sender_field
        return event

    def __call__(self, model):
        [event.connect_model(model) for event in values(self.events) if event]
        model.webhook_events = self
        return model
