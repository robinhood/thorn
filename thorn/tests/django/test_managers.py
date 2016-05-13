from __future__ import absolute_import, unicode_literals

from thorn.django.models import Subscriber

from django.contrib.auth import get_user_model

from thorn.tests.case import Case


class test_SubscriberManager(Case):

    def setUp(self):
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
        try:
            self.subscribers = [
                self.rsimple('foo.*', 'A'),
                self.rsimple('foo.created', 'B'),
                self.rsimple('foo.created', 'C'),
                self.rsimple('foo.deleted', 'D'),
                self.rsimple('*.created', 'E'),
                self.rsimple('bar.updated', 'F'),
                self.rsimple('baz.*', 'G', user=self.user2),
            ]
        except BaseException:  # pragma: no cover
            raise

    def tearDown(self):
        self.user.delete()
        [r.delete() for r in self.subscribers]

    def rsimple(self, event, url, user=None):
        return Subscriber.objects.create(
            event=event, url=url, user=user or self.user,
        )

    def test_matching(self):
        self.assertFalse(
            Subscriber.objects.matching('baz.moo', user=self.user)
        )
        self.assertListEqual(
            [r.url for r in Subscriber.objects.matching(
                'baz.moo', user=self.user2)],
            ['G'],
        )

    def test_matching_event(self):
        self.assertListEqual(
            [r.url for r in Subscriber.objects.matching_event('bar.updated')],
            ['F'],
        )

    def test_matching_event__glob(self):
        self.assertListEqual(
            [r.url for r in Subscriber.objects.matching_event('foo.created')],
            ['A', 'B', 'C', 'E'],
        )
        self.assertListEqual(
            [r.url for r in Subscriber.objects.matching_event('foo.updated')],
            ['A'],
        )
        self.assertListEqual(
            [r.url for r in Subscriber.objects.matching_event('foo.deleted')],
            ['A', 'D'],
        )
        self.assertListEqual(
            [r.url for r in Subscriber.objects.matching_event('baz.created')],
            ['E', 'G'],
        )
        self.assertListEqual(
            [r.url for r in Subscriber.objects.matching_event('bar.deleted')],
            [],
        )
