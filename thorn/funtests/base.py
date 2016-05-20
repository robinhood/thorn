"""

    thorn.funtests.base
    =================================

    Extends Cyanide stress test suite with utilities used
    to test Thorn.

"""
from __future__ import absolute_import, unicode_literals

import hashlib
import json
import requests

from contextlib import contextmanager
from six import iteritems as items, itervalues as values
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse

from cyanide.suite import Suite, testcase
from itsdangerous import Signer

from thorn.django.models import Subscriber

from testapp.models import Article, SubscriberLog, Tag

BASE_URL = 'http://localhost:8000'

__all__ = ['WebhookSuite', 'new_ref', 'url', 'event_url', 'testcase']


def new_ref():
    return uuid4().hex


def url(*s):
    return '/'.join((BASE_URL,) + s)


def event_url(event, ref=None, rest=None):
    return url('r', event, '?ref={0}{1}'.format(ref, rest or ''))


class WebhookSuite(Suite):
    user = user2 = None
    token = None
    token_type = 'Token'

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
            event=event, url=self._event_url(event, ref, rest),
        )

    def unsubscribe(self, url):
        return self._delete(url)

    def list_subscriptions(self):
        return self.get('hooks/')

    def _event_url(self, event, ref=None, rest=None):
        return event_url(event, ref=ref or self.ref, rest=rest)

    def assert_article_event_received(self, article, event, sub=None,
                                      reverse=None, ref=None, n=1):
        logs = self.wait_for_webhook_received(ref or self.ref, maxlen=n)
        assert len(logs) == n
        if sub is not None:
            hmac_secret = sub['hmac_secret']
            if hmac_secret:
                log = SubscriberLog.objects.filter(ref=ref or self.ref)[0]
                assert Signer(
                    hmac_secret,
                    digest_method=hashlib.sha256).get_signature(
                        log.data) == log.hmac
        self.assert_log_matches(
            logs[0],
            event=event,
            ref=reverse or self.reverse_article(article),
            data=article.webhook_payload(),
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
        return self._request(requests.get, 'data', url(*path), data)

    def post(self, *path, **data):
        return self._request(requests.post, 'json', url(*path), data)

    def delete(self, *path, **data):
        return self._request(requests.delete, 'json', url(*path), data)

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
