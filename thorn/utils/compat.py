"""

    thorn.utils.compat
    ==================

    Python version compatibility utilities.

"""
from __future__ import absolute_import, unicode_literals

import sys

__all__ = ['bytes_if_py2']

PY3 = sys.version_info[0] >= 3

if PY3:  # pragma: no cover
    def bytes_if_py2(s):
        return s

    def to_bytes(s):
        return s.encode() if isinstance(s, str) else s
    bytes_if_py3 = to_bytes

else:  # pragma: no cover
    def to_bytes(s):  # noqa
        return s.encode() if isinstance(s, unicode) else s
    bytes_if_py2 = to_bytes

    def bytes_if_py3(s):  # noqa
        return s


def restore_from_keys(fun, args, kwargs):
    return fun(*args, **kwargs)
