from __future__ import absolute_import, unicode_literals

import pytest

from thorn import validators
from thorn.exceptions import SecurityError


def test_deserialize_validator():
    concrete = [
        validators.block_internal_ips(),
        validators.ensure_port(80, 443, 21, 6453),
        validators.ensure_protocol('https', 'http', 'ftp'),
        validators.block_cidr_network('192.168.0.0/16'),
    ]
    svalidators = [validators.serialize_validator(v) for v in concrete]
    re = [validators.deserialize_validator(v) for v in svalidators]

    with pytest.raises(SecurityError):
        re[0]('127.0.0.1')
    re[0]('123.123.123.123')
    with pytest.raises(SecurityError):
        re[1]('http://example.com:1234')
    re[1]('http://example.com')
    re[1]('http://example.com:80')
    re[1]('http://example.com:6453')
    with pytest.raises(SecurityError):
        re[2]('gopher://mozilla')
    re[2]('http://example.com:80/path/?q=1')
    re[2]('https://example.com')
    re[2]('ftp://example.com')
    with pytest.raises(SecurityError):
        re[3]('192.168.3.1')
    re[3]('123.123.123.123')
