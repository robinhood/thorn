"""

    thorn.models
    ============

    Generic base model mixins.

"""
from __future__ import absolute_import, unicode_literals

import hashlib

from six import string_types

from itsdangerous import Signer


def get_digest(d):
    assert d in hashlib.algorithms_available
    return getattr(hashlib, d)


class SubscriberModelMixin(object):

    def _user_ident(self):
        return (getattr(self, self.user_id_field)
                if self.user_id_field else self.user)

    def as_dict(self):
        return {
            'event': self.event,
            'user': self._user_ident(),
            'url': self.url,
            'hmac_secret': self.hmac_secret,
            'hmac_digest': self.hmac_digest,
            'content_type': self.content_type,
        }

    def sign(self, text):
        return Signer(
            self.hmac_secret,
            digest_method=get_digest(self.hmac_digest)).get_signature(text)

    @classmethod
    def from_dict(cls, *args, **kwargs):
        if args and isinstance(args[0], string_types):
            args = ({'url': args[0]},)
        return cls(**dict(*args, **kwargs))
