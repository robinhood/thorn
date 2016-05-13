"""

    thorn.exceptions
    ================

    Thorn-related exceptions.

"""
from __future__ import absolute_import, unicode_literals


class ThornError(Exception):
    pass


class ImproperlyConfigured(ThornError):
    pass


class SecurityError(ThornError):
    pass
