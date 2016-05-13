from __future__ import absolute_import, unicode_literals

from thorn.django.models import Subscriber

from kombu.five import text_t

from django.contrib.auth import get_user_model

from thorn.tests.case import Case


class test_Subscriber(Case):

    def setUp(self):
        self.user = get_user_model()(username='george')
        self.subscriber = Subscriber(
            event='foo.created', user=self.user, url='http://example.com',
        )

    def test_str(self):
        self.assertTrue(text_t(self.subscriber))

    def test_as_dict(self):
        self.assertDictEqual(self.subscriber.as_dict(), {
            'event': self.subscriber.event,
            'user': self.subscriber.user.pk,
            'url': self.subscriber.url,
            'content_type': self.subscriber.content_type,
            'hmac_secret': self.subscriber.hmac_secret,
            'hmac_digest': self.subscriber.hmac_digest,
        })

    def test_from_dict__arg(self):
        x = Subscriber.from_dict('http://e.com', event='foo.bar')
        self.assertIsInstance(x, Subscriber)
        self.assertEqual(x.url, 'http://e.com')
        self.assertEqual(x.event, 'foo.bar')

    def test_from_dict__dict(self):
        x = Subscriber.from_dict(url='http://e.com', event='foo.bar')
        self.assertIsInstance(x, Subscriber)
        self.assertEqual(x.url, 'http://e.com')
        self.assertEqual(x.event, 'foo.bar')
