from __future__ import absolute_import, unicode_literals

import celery
import json
import os
import pytest
import requests
import threading

from contextlib import contextmanager
from six import iteritems as items, itervalues as values
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse

from celery.result import allow_join_result, _set_task_join_will_block
from cyanide.suite import DummyMeter, ManagerMixin
from cyanide.tasks import add

from thorn.django.models import Subscriber
from thorn.utils import hmac

from testapp.models import Article, SubscriberLog, Tag

BASE_URL = 'http://localhost:8000'

NO_WORKER = os.environ.get('NO_WORKER')
WORKER_LOGLEVEL = os.environ.get('WORKER_LOGLEVEL', 'error')


# This Django setup is here to make sure the worker sees db changes.

@pytest.fixture(scope='session')
def django_db_setup():
    settings.DATABASES['default']['name'] = os.path.join(
        settings.BASE_DIR, 'db.sqlite3')


@pytest.fixture(scope='session')
def django_db_modify_db_settings():
    pass


@pytest.fixture(scope='session')
def django_db_use_migrations():
    return True


@pytest.fixture(scope='session')
def django_db_keepdb():
    return True

# django stuff fin.


@pytest.fixture(scope='session')
def _celery_app():
    from .celery import app
    return app


@pytest.fixture(scope='session')
def celery_worker(_celery_app):
    if not NO_WORKER:
        on_started = threading.Event()

        def on_worker_ready(consumer):
            on_started.set()

        _celery_app.set_current()
        _celery_app.set_default()
        _celery_app.finalize()
        _celery_app.log.setup()

        # Make sure we can connect to the broker
        with _celery_app.connection() as conn:
            conn.default_channel.queue_declare

        if celery.VERSION >= (4,):
            pool_args = {'pool': 'solo'}
        else:
            pool_args = {'pool_cls': 'solo'}

        worker = _celery_app.WorkController(
            concurrency=1,
            loglevel=WORKER_LOGLEVEL,
            logfile=None,
            ready_callback=on_worker_ready,
            **pool_args)
        t = threading.Thread(target=worker.start)
        t.start()

        assert any(t.startswith('thorn.') for t in _celery_app.tasks)
        assert 'cyanide.tasks.add' in _celery_app.tasks

        on_started.wait()

        with allow_join_result():
            assert add.delay(2, 2).get(timeout=3) == 4
        _set_task_join_will_block(False)
        yield worker
        worker.stop()
        t.join()


def new_ref():
    """Create new reference ID."""
    return uuid4().hex


@pytest.fixture
def celery_app(_celery_app, request):
    _celery_app.finalize()
    _celery_app.set_current()
    yield _celery_app


@pytest.fixture
def manager(celery_app, celery_worker, live_server, transactional_db):
    with Manager(celery_app, base_url=live_server.url) as manager:
        yield manager


class Manager(ManagerMixin):
    """Thorn manager."""

    # we don't stop full suite when a task result is missing.
    TaskPredicate = AssertionError
    Meter = DummyMeter

    user = user2 = None
    token = None
    token_type = 'Token'

    def __init__(self, app, no_join=False, base_url=BASE_URL, **kwargs):
        self.app = app
        self.no_join = no_join
        self.base_url = base_url
        self._init_manager(app, **kwargs)

    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self):
        pass

    def url(self, *s):
        """Create URL by components in *s."""
        return '/'.join((self.base_url,) + s)

    def event_url(self, event, ref=None, rest=None):
        """Return url for event."""
        ref = ref or self.ref
        return self.url('r', event, '?ref={0}{1}'.format(ref, rest or ''))

    def setup(self):
        Article.objects.all().delete()
        Tag.objects.all().delete()
        SubscriberLog.objects.all().delete()
        Subscriber.objects.all().delete()

        self.user = self._get_user('test', 'test')
        self.user2 = self._get_user('test2', 'test2')
        self.token = self._login()
        self.ref = new_ref()
        assert not SubscriberLog.objects.filter(ref=self.ref)

    def create_article(self, title, state='PENDING', author=None):
        return Article.objects.create(
            title=title, state=state, author=author or self.user,
        )

    def assert_webhook_not_received(self, ref=None):
        return self.ensure_not_for_a_while(
            SubscriberLog.objects.get, SubscriberLog.DoesNotExist,
            desc='webhook received [ref={0}]'.format(ref or self.ref),
            kwargs={'ref': ref or self.ref},
        )

    def subscribe(self, event, ref=None, rest=None):
        return self.post(
            'hooks/',
            event=event, url=self.event_url(event, ref, rest),
        )

    def unsubscribe(self, url):
        return self._delete(url)

    def list_subscriptions(self):
        return self.get('hooks/')

    def assert_article_event_received(self, article, event, sub=None,
                                      reverse=None, ref=None, n=1):
        logs = self.wait_for_webhook_received(ref or self.ref, maxlen=n)
        assert len(logs) == n
        if sub is not None:
            hmac_secret = sub['hmac_secret']
            log = SubscriberLog.objects.filter(ref=ref or self.ref)[0]
            if hmac_secret:
                assert hmac.verify(log.hmac, 'sha256', hmac_secret, log.data)
            assert log.subscription == sub['id']

        self.assert_log_matches(
            logs[0],
            event=event,
            ref=reverse or self.reverse_article(article),
            data=article.webhooks.payload(article),
        )

    def reverse_article(self, article):
        return reverse('article:detail', kwargs={'id': article.pk})

    def wait_for_webhook_received(self, ref=None, maxlen=1):
        return self.wait_for(
            self.assert_log, Exception,
            'webhook (ref={0})'.format(ref or self.ref),
            args=(ref or self.ref, maxlen),
        )

    def assert_log(self, ref=None, maxlen=1):
        logs = SubscriberLog.objects.filter(ref=ref or self.ref)
        assert logs and (len(logs) == maxlen if maxlen else True)
        return [json.loads(entry.data) for entry in logs]

    def assert_log_matches(self, log, **expected):
        for k, v in items(expected):
            assert log[k] == v, 'key={0} expected {1} == {2}'.format(
                k, v, log[k])

    def _login(self, username='test', password='test'):
        return self.post(
            'api-token-auth/',
            username=username,
            password=password,
        )['token']

    def _get_user(self, username, password, email='test@example.com'):
        try:
            return get_user_model().objects.create_user(
                username=username, password=password, email=email,
            )
        except Exception:
            return get_user_model().objects.get(username=username)

    def headers(self):
        if self.token:
            return {
                'Authorization': ' '.join([
                    self.token_type.capitalize(), self.token,
                ])
            }
        return {}

    @contextmanager
    def override_worker_setting(self, setting_name, new_value):
        old_value = list(values(self.setenv(setting_name, new_value)))[0]
        try:
            yield
        finally:
            self.setenv(setting_name, old_value)

    @contextmanager
    def worker_subscribe_to(self, event, url=None, callback=None):
        self.hook_subscribe(event, url=url, callback=callback)
        try:
            yield
        finally:
            self.hook_clear(event)

    def setenv(self, setting_name, new_value):
        return self.app.control.inspect()._request(
            'setenv', setting_name=setting_name, new_value=new_value)

    def assert_ok_pidbox_response(self, replies):
        for reply in values(replies):
            if not reply['ok']:
                raise RuntimeError(
                    'Worker remote control command raised: {0!r}'.format(
                        reply.get('error', reply)))
        return replies

    def hook_subscribe(self, event, url, callback=None):
        return self.assert_ok_pidbox_response(
            self.app.control.inspect()._request(
                'hook_subscribe', event=event, url=url, callback=callback,
            ),
        )

    def hook_unsubscribe(self, event, url):
        return self.assert_ok_pidbox_response(
            self.app.control.inspect()._request(
                'hook_unsubscribe', event=event, url=url,
            ),
        )

    def hook_clear(self, event):
        return self.assert_ok_pidbox_response(
            self.app.control.inspect()._request(
                'hook_clear', event=event,
            )
        )

    def get(self, *path, **data):
        return self._request(requests.get, 'data', self.url(*path), data)

    def post(self, *path, **data):
        return self._request(requests.post, 'json', self.url(*path), data)

    def delete(self, *path, **data):
        return self._request(requests.delete, 'json', self.url(*path), data)

    def _delete(self, url, **data):
        return self._request(requests.delete, 'json', url, data)

    def _request(self, fun, data_key, url, data):
        response = fun(url, headers=self.headers(), **{data_key: data})
        try:
            response.raise_for_status()
        except Exception:
            self.error('HTTP response body was: {0!r}'.format(
                response.content))
            raise
        return response.json() if response.content else None
