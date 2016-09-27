from __future__ import absolute_import, unicode_literals

import pytest

from case import Mock

from thorn.conf import Settings, event_choices, all_settings
from thorn.exceptions import ImproperlyConfigured


@pytest.fixture()
def app():
    return Mock(name='app')


@pytest.mark.parametrize('setting,default_attr', [
    ('THORN_CHUNKSIZE', 'default_chunksize'),
    ('THORN_CODECS', 'default_codecs'),
    ('THORN_DISPATCHER', 'default_dispatcher'),
    ('THORN_DRF_PERMISSION_CLASSES', 'default_drf_permission_classes'),
    ('THORN_EVENT_CHOICES', 'default_event_choices'),
    ('THORN_EVENT_TIMEOUT', 'default_timeout'),
    ('THORN_HMAC_SIGNER', 'default_hmac_signer'),
    ('THORN_SIGNAL_HONORS_TRANSACTION', 'default_signal_honors_transaction'),
])
def test_settings(setting, default_attr, app):
    s1 = Settings(app=app)
    setattr(app.config, setting, None)
    assert getattr(s1, setting) == getattr(s1, default_attr)

    setattr(app.config, setting, 'just')
    s2 = Settings(app=app)
    assert getattr(s2, setting) == 'just'


def test_THORN_SUBSCRIBERS(app):
    app.config.THORN_SUBSCRIBERS = None
    assert Settings(app=app).THORN_SUBSCRIBERS == {}
    app.config.THORN_SUBSCRIBERS = 'just'
    assert Settings(app=app).THORN_SUBSCRIBERS == 'just'


def test_THORN_SUBSCRIBER_MODEL(app):
    app.config.THORN_SUBSCRIBER_MODEL = None
    assert Settings(app=app).THORN_SUBSCRIBER_MODEL is None


class test_event_choices:

    def test_wrong_type(self, app):
        app.settings.THORN_EVENT_CHOICES = 3
        with pytest.raises(ImproperlyConfigured):
            event_choices(app=app)

    def test(self, app):
        app.settings.THORN_EVENT_CHOICES = ('a.b', 'c.d', 'e.f')
        assert event_choices(app=app) == [
            ('a.b', 'a.b'), ('c.d', 'c.d'), ('e.f', 'e.f')
        ]


def test_all_settings():
    assert all_settings()
