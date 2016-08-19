from __future__ import absolute_import, unicode_literals

import pytest

from case import mock

from thorn.environment.django import DjangoEnv


@pytest.fixture()
def env():
    return DjangoEnv()


@pytest.fixture()
def symbol_by_name(patching):
    return patching('thorn.environment.django.symbol_by_name')


@mock.environ('DJANGO_SETTINGS_MODULE', '')
def test_autodetect__when_no_django(env):
    assert not env.autodetect()


@mock.environ('DJANGO_SETTINGS_MODULE', 'proj.settings')
def test_autodetect__when_django(env):
    assert env.autodetect()


def test_config(env, symbol_by_name):
    assert env.config is symbol_by_name.return_value
    symbol_by_name.assert_called_once_with(env.settings_cls)


def test_Subscriber(env, symbol_by_name):
    env.config.THORN_SUBSCRIBER_MODEL = None
    assert env.Subscriber is symbol_by_name.return_value
    symbol_by_name.assert_called_with(env.subscriber_cls)


def test_Subscribers(env, symbol_by_name):
    env.config.THORN_SUBSCRIBER_MODEL = None
    assert env.Subscribers is symbol_by_name.return_value.objects
    symbol_by_name.assert_called_with(env.subscriber_cls)


def test_signals(patching, env):
    import_module = patching('importlib.import_module')
    assert env.signals is import_module.return_value
    import_module.assert_called_with(env.signals_cls)


def test_reverse(env, symbol_by_name):
    assert env.reverse is symbol_by_name.return_value
    symbol_by_name.assert_called_once_with(env.reverse_cls)
