"""

    thorn.models
    ============

    Generic base model mixins.

"""
from __future__ import absolute_import, unicode_literals

import hashlib

from abc import ABCMeta, abstractmethod, abstractproperty
from six import string_types

from celery.five import with_metaclass
from itsdangerous import Signer

__all__ = ['AbstractSubscriber', 'SubscriberModelMixin', 'get_digest']


def get_digest(d):
    assert d in hashlib.algorithms_available
    return getattr(hashlib, d)


@with_metaclass(ABCMeta)
class AbstractSubscriber(object):

    #: Unique identifier.
    uuid = abstractproperty()

    #: Event pattern this subscriber is subscribed to (e.g. ``article.*``).
    event = abstractproperty()

    #: Destination URL to dispatch this event.
    url = abstractproperty()

    #: User filter: when set only dispatch if the event sender matches.
    user = abstractproperty()

    #: HMAC secret key, of arbitrary length.
    hmac_secret = abstractproperty()

    #: HMAC digest type (e.g. ``"sha512"``).
    #:
    #: The value used must be a member of :data:`hashlib.algorithms_available`.
    hmac_digest = abstractproperty()

    #: MIME-type to use for web requests made to the subscriber :attr:`url`.
    content_type = abstractproperty()

    @abstractmethod
    def as_dict(self):
        """Dictionary representation of Subscriber."""
        pass  # pragma: no cover

    @abstractmethod
    def from_dict(self, *args, **kwargs):
        """Create subscriber from dictionary representation.

        Accept the same arguments as :class:`dict`.

        """
        pass  # pragma: no cover

    @abstractmethod
    def sign(self, message):
        """Sign (HMAC) message using :attr:`hmac_secret` and the current
        :attr:`hmac_digest` type."""
        pass  # pragma: no cover

    @abstractmethod
    def user_ident(self):
        """Return :attr:`user` identity, must be json serializable like a
        database primary key."""
        pass  # pragma: no cover

    @classmethod
    def register(cls, other):
        # we override `register` to return other for use as a decorator.
        type(cls).register(cls, other)
        return other


@AbstractSubscriber.register
class SubscriberModelMixin(object):

    @classmethod
    def from_dict(cls, *args, **kwargs):
        if args and isinstance(args[0], string_types):
            args = ({'url': args[0]},)
        return cls(**dict(*args, **kwargs))

    def as_dict(self):
        return {
            'event': self.event,
            'user': self.user_ident(),
            'url': self.url,
            'hmac_secret': self.hmac_secret,
            'hmac_digest': self.hmac_digest,
            'content_type': self.content_type,
        }

    def sign(self, message):
        return Signer(
            self.hmac_secret,
            digest_method=get_digest(self.hmac_digest)).get_signature(message)
