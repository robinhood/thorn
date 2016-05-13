from __future__ import absolute_import, unicode_literals

from thorn.conf import Settings, event_choices, all_settings
from thorn.exceptions import ImproperlyConfigured

from .case import Case, Mock


class test_Settings(Case):

    attributes = [
        ('THORN_CHUNKSIZE', 'default_chunksize'),
        ('THORN_CODECS', 'default_codecs'),
        ('THORN_DISPATCHER', 'default_dispatcher'),
        ('THORN_DRF_PERMISSION_CLASSES', 'default_drf_permission_classes'),
        ('THORN_EVENT_CHOICES', 'default_event_choices'),
        ('THORN_EVENT_TIMEOUT', 'default_timeout'),
    ]

    def setup(self):
        self.app = Mock(name='app')

    def test_settings(self):
        for key_attr, default_attr in self.attributes:
            s1 = Settings(app=self.app)
            setattr(self.app.config, key_attr, None)
            self.assertEqual(
                getattr(s1, key_attr), getattr(s1, default_attr), key_attr)

            setattr(self.app.config, key_attr, 'just')
            s2 = Settings(app=self.app)
            self.assertEqual(getattr(s2, key_attr), 'just', key_attr)

    def test_THORN_SUBSCRIBERS(self):
        self.app.config.THORN_SUBSCRIBERS = None
        self.assertDictEqual(Settings(app=self.app).THORN_SUBSCRIBERS, {})
        self.app.config.THORN_SUBSCRIBERS = 'just'
        self.assertEqual(Settings(app=self.app).THORN_SUBSCRIBERS, 'just')


class test_event_choices(Case):

    def setup(self):
        self.app = Mock(name='app')

    def test_wrong_type(self):
        self.app.settings.THORN_EVENT_CHOICES = 3
        with self.assertRaises(ImproperlyConfigured):
            event_choices(app=self.app)

    def test(self):
        self.app.settings.THORN_EVENT_CHOICES = ('a.b', 'c.d', 'e.f')
        self.assertListEqual(
            event_choices(app=self.app),
            [('a.b', 'a.b'), ('c.d', 'c.d'), ('e.f', 'e.f')],
        )


class test_all_settings(Case):

    def test(self):
        self.assertTrue(all_settings())
