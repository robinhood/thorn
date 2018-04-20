from __future__ import absolute_import, unicode_literals

import pytest

from thorn.django.models import Subscriber

from django.contrib.auth import get_user_model


@pytest.mark.django_db()
class test_SubscriberManager:

    @pytest.fixture(autouse=True)
    def setup_self(self):
        self.user, _ = get_user_model().objects.get_or_create(
            username='test_Subscriber',
            password='iesf&83j2aswe2',
            email='example@example.com',
        )
        self.user2, _ = get_user_model().objects.get_or_create(
            username='test_Subscriber2',
            password='asdjqwej21j2344',
            email='example2@example.com',
        )
        self.subscribers = [
            self.rsimple('foo.*', 'A'),
            self.rsimple('foo.created', 'B'),
            self.rsimple('foo.created', 'C'),
            self.rsimple('foo.deleted', 'D'),
            self.rsimple('*.created', 'E'),
            self.rsimple('bar.updated', 'F'),
            self.rsimple('baz.*', 'G', user=self.user2),
            self.rsimple('*', 'H'),
        ]

    def rsimple(self, event, url, user=None):
        return Subscriber.objects.create(
            event=event, url=url, user=user or self.user,
        )

    @pytest.mark.parametrize('event,expected,username', [
        ('foo.created', ['A', 'B', 'C', 'E', 'H'], None),
        ('foo.updated', ['A', 'H'], None),
        ('foo.deleted', ['A', 'D', 'H'], None),
        ('baz.created', ['E', 'G', 'H'], None),
        ('bar.updated', ['F', 'H'], None),
        ('bar.deleted', ['H'], None),
        ('baz.moo', ['H'], 'user'),
        ('baz.moo', ['G'], 'user2')
    ])
    def test_matching(self, event, expected, username):
        assert expected == [
            r.url for r in Subscriber.objects.matching(
                event,
                user=getattr(self, username) if username else None,
            )
        ]
