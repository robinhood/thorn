"""Thorn-related exceptions."""
from __future__ import absolute_import, unicode_literals


class ThornError(Exception):
    """Base class for Thorn exceptions."""


class ImproperlyConfigured(ThornError):
    """Configuration invalid/missing."""


class SecurityError(ThornError):
    """Security related error."""


class BufferNotEmpty(Exception):
    """Trying to close buffer that is not empty."""
