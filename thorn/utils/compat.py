"""Python version compatibility utilities."""
from __future__ import absolute_import, unicode_literals

import sys

__all__ = ['bytes_if_py2']

PY3 = sys.version_info[0] >= 3

if PY3:  # pragma: no cover
    def bytes_if_py2(s):
        """Convert str to bytes if running under Python 2."""
        return s

    def want_bytes(s):
        """Convert str to bytes."""
        return s.encode() if isinstance(s, str) else s
    bytes_if_py3 = want_bytes

else:  # pragma: no cover
    def want_bytes(s):  # noqa
        """Convert str to bytes."""
        return s.encode() if isinstance(s, unicode) else s
    bytes_if_py2 = want_bytes

    def bytes_if_py3(s):  # noqa
        """Convert str to bytes if running under Python 3."""
        return s


def restore_from_keys(fun, args, kwargs):
    """Pickle helper to support kwargs in ``__reduce__``."""
    return fun(*args, **kwargs)
