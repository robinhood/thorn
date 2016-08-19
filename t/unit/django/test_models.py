from __future__ import absolute_import, unicode_literals

import pytest

from thorn.django.models import Subscriber

from kombu.five import text_t

from django.contrib.auth import get_user_model


@pytest.fixture()
def user():
    return get_user_model()(username='george')


@pytest.fixture()
def subscriber(user):
    return Subscriber(
        event='foo.created', user=user, url='http://example.com',
    )


class test_Subscriber:

    def test_str(self, subscriber):
        assert text_t(subscriber)

    def test_as_dict(self, subscriber):
        assert subscriber.as_dict() == {
            'event': subscriber.event,
            'user': subscriber.user.pk,
            'url': subscriber.url,
            'content_type': subscriber.content_type,
            'hmac_secret': subscriber.hmac_secret,
            'hmac_digest': subscriber.hmac_digest,
            'uuid': str(subscriber.uuid),
        }

    def test_from_dict__arg(self):
        x = Subscriber.from_dict('http://e.com', event='foo.bar')
        assert isinstance(x, Subscriber)
        assert x.url == 'http://e.com'
        assert x.event == 'foo.bar'

    def test_from_dict__dict(self):
        x = Subscriber.from_dict(url='http://e.com', event='foo.bar')
        assert isinstance(x, Subscriber)
        assert x.url == 'http://e.com'
        assert x.event == 'foo.bar'
