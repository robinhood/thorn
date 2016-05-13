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
else:  # pragma: no cover
    def bytes_if_py2(s):  # noqa
        if isinstance(s, unicode):
            return s.encode()
        return s


def restore_from_keys(fun, args, kwargs):
    return fun(*args, **kwargs)
