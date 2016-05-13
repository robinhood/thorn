"""

    thorn.models
    ============

    Generic base model mixins.

"""
from __future__ import absolute_import, unicode_literals

from six import string_types


class SubscriberModelMixin(object):

    def _user_ident(self):
        return (getattr(self, self.user_id_field)
                if self.user_id_field else self.user)

    def as_dict(self):
        return {
            'event': self.event,
            'user': self._user_ident(),
            'url': self.url,
            'content_type': self.content_type,
        }

    @classmethod
    def from_dict(cls, *args, **kwargs):
        if args and isinstance(args[0], string_types):
            args = ({'url': args[0]},)
        return cls(**dict(*args, **kwargs))
