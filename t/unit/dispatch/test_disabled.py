from __future__ import absolute_import, unicode_literals

from thorn.dispatch.disabled import Dispatcher


def test_send():
    Dispatcher().send(data={'foo': 'bar'})
