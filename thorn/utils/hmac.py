"""

    thorn.utils.hmac
    ================

    HMAC Message signing utilities.

"""
from __future__ import absolute_import, unicode_literals

import base64
import hashlib
import hmac
import random
import string

from .compat import bytes_if_py3, to_bytes

try:
    import itsdangerous
except ImportError:  # pragma: no cover
    itsdangerous = None  # noqa

# Some version of PyPy does not have hashlib.algorithms_available
allowed_algorithms = {
    'sha1', 'sha224', 'sha256', 'sha384', 'sha512',
}

punctuation = string.punctuation.replace('"', '').replace("'", '')


def get_digest(d):
    assert d.lower() in allowed_algorithms, d.lower()
    return getattr(hashlib, d.lower())


def sign(digest_method, key, message):
    return base64.b64encode(bytes_if_py3(hmac.new(
        to_bytes(key),
        to_bytes(message),
        digestmod=get_digest(digest_method)).digest()))


def verify(digest, digest_method, key, message):
    return hmac.compare_digest(
        to_bytes(sign(digest_method, key, message)),
        to_bytes(digest))


def random_secret(
        length, chars=string.ascii_letters + string.digits + punctuation):
    return ''.join(random.choice(chars) for _ in range(length))


def compat_sign(digest_method, key, message):
    return itsdangerous.Signer(
        key, digest_method=get_digest(digest_method),
    ).get_signature(message)
