"""Webhook decorators."""
from __future__ import absolute_import, unicode_literals
import inspect
from itertools import chain
from six import iteritems as items, itervalues as values
from .utils.compat import bytes_if_py2


def webhook_model(*args, **kwargs):
    # type: (*Any, **Any) -> Any
    """Decorate model to send webhooks based on changes to that model.

    Keyword Arguments:
        on_create (~thorn.Event): Event to dispatch whenever an instance of
            this model is created (``post_save``).
        on_change (~thorn.Event): Event to dispatch whenever an instance of
            this model is changed (``post_save``).
        on_delete (~thorn.Event): Event to dispatch whenever an instance of
            this model is deleted (``post_delete``).
        on_$event (~thorn.Event): Additional user defined events.,

        sender_field (str):
            Default field used as a sender for events, e.g. ``"account.user"``,
            will use ``instance.account.user``.

            Individual events can override the sender field user.
        reverse (Callable):
            A :class:`thorn.reverse.model_reverser` instance (or any callable
            taking an model instance as argument), that describes how to get
            the URL for an instance of this model.

            Individual events can override the reverser used.

            Note: On Django you can instead define a `get_absolute_url`
            method on the Model.

    Examples:
        Simple article model, where the URL reference is retrieved
        by ``reverse('article-detail', kwargs={'uuid': article.uuid})``:

        .. code-block:: python

            @webhook_model
            class Article(models.Model):
                uuid = models.UUIDField()

                class webhooks:
                    on_create = ModelEvent('article.created')
                    on_change = ModelEvent('article.changed')
                    on_delete = ModelEvent('article.removed')
                    on_deactivate = ModelEvent(
                        'article.deactivate', deactivated__eq=True,
                    )

                @models.permalink
                def get_absolute_url(self):
                    return ('blog:article-detail', None, {'uuid': self.uuid})

        The URL may not actually exist after deletion, so maybe we want
        to point the reference to something else in that special case,
        like a category that can be reversed by doing
        ``reverse('category-detail', args=[article.category.name])``.

        We can do that by having the ``on_delete`` event override
        the method used to get the absolute url (reverser), for that event
        only:

        .. code-block:: python

            @webhook_model
            class Article(model.Model):
                uuid = models.UUIDField()
                category = models.ForeignKey('category')

                class webhooks:
                    on_create = ModelEvent('article.created')
                    on_change = ModelEvent('article.changed')
                    on_delete = ModelEvent(
                        'article.removed',
                        reverse=model_reverser(
                            'category:detail', 'category.name'),
                    )
                    on_hipri_delete = ModelEvent(
                        'article.internal_delete', priority__gte=30.0,
                    ).dispatches_on_delete()

                @models.permalink
                def get_absolute_url(self):
                    return ('blog:article-detail', None, {'uuid': self.uuid})
    """
    def _augment_model(model):
        # type: (type) -> type
        try:
            Webhooks = model.webhooks
        except AttributeError:
            Webhooks, attrs, handlers = None, {}, {}
        else:
            if not inspect.isclass(Webhooks):
                raise TypeError(
                    'Model.webhooks is not a class, but {0!r}'.format(
                        type(Webhooks)))
            # get all the attributes from the webhooks class description.
            attrs = dict(Webhooks.__dict__)
            # extract all the `on_*` event handlers.
            handlers = {k: v for k, v in items(attrs) if k.startswith('on_')}
            # preserve non-event handler attributes.
            attrs = {k: v for k, v in items(attrs) if k not in handlers}
        if Webhooks is None or not issubclass(Webhooks, WebhookCapable):
            # Model.webhooks should inherit from WebhookCapable.
            # Note that we keep this attribute for introspection purposes
            # only (kind of like Model._meta), it doesn't implement
            # any functionality at this point.
            Webhooks = type(
                bytes_if_py2('webhooks'), (WebhookCapable,), attrs)
        model_webhooks = Webhooks(**dict(handlers, **kwargs))
        return model_webhooks.contribute_to_model(model)

    if len(args) == 1:
        if callable(args[0]):
            return _augment_model(*args)
        raise TypeError('argument 1 to @webhook_model() must be a callable')
    if args:
        raise TypeError(
            '@webhook_model() takes exactly 1 argument ({0} given)'.format(
                sum([len(args), len(kwargs)])))
    return _augment_model


class WebhookCapable(object):
    """Implementation of model.webhooks.

    The decorator sets model.webhooks to be an instance of this type.
    """

    reverse = None          # type: model_reverser
    sender_field = None     # type: str
    events = None           # type: Mapping[str, Event]

    def __init__(self,
                 on_create=None, on_change=None, on_delete=None,
                 reverse=None, sender_field=None, **kwargs):
        # type: (Event, Event, Event, model_reverser, str, **Any) -> None
        self.events = {}
        if reverse is not None:
            self.reverse = reverse
        if sender_field is not None:
            self.sender_field = sender_field
        self.update_events(
            {k: v for k, v in items(kwargs) if k.startswith('on_')},
            on_create=on_create and on_create.dispatches_on_create(),
            on_change=on_change and on_change.dispatches_on_change(),
            on_delete=on_delete and on_delete.dispatches_on_delete(),
        )

    def update_events(self, events, **kwargs):
        # type: (Mapping[str, Event], **Any) -> None
        self.events.update(self.connect_events(events, **kwargs))

    def connect_events(self, events, **kwargs):
        # type: (Mapping[str, Event], **Any) -> Mapping[str, Event]
        return {
            k: self.contribute_to_event(v)
            for k, v in chain(items(events), items(kwargs))
        }

    def contribute_to_event(self, event):
        # type: (Event) -> Event
        if event:
            if event.reverse is None:
                event.reverse = self.reverse
            event.sender_field = self.sender_field
        return event

    def contribute_to_model(self, model):
        # type: (type) -> type
        [event.connect_model(model) for event in values(self.events) if event]
        model.webhooks = self
        model.webhook_events = self  # XXX remove for Thorn 2.0
        return model

    def payload(self, instance):
        return self.delegate_to_model(instance, 'webhook_payload')

    def headers(self, instance):
        return self.delegate_to_model(instance, 'webhook_headers')

    def delegate_to_model(self, instance, meth, *args, **kwargs):
        # type: (Model, str, *Any, **Any) -> Any
        fun = getattr(instance, meth, None)
        if fun is not None:
            return fun(*args, **kwargs)

    def __getitem__(self, key):
        # type: (str) -> Any
        return self.events[key]

    def __setitem__(self, key, value):
        # type: (str, Any) -> None
        self.events[key] = value

    def __delitem__(self, key):
        # type: (str) -> None
        del self.events[key]
