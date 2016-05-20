"""

    thorn.funtests.suite
    =================================

    Functional test suite.

    Instructions
    ------------

    #. Start the celery worker:

    .. code-block:: console

        $ celery -A thorn.funtests worker -l info -P eventlet -c 1000

    #. Start the development web server:

        .. code-block:: console

            $ (cd testproj; python manage.py runserver)

    #. Then execute the functional test suite:

        .. code-block:: console

            $ celery -A thorn.funtests cyanide


    For a list of tests that you can select see:

    .. code-block:: console

        $ celery -A thorn.funtests cyanide -l

"""
from __future__ import absolute_import, unicode_literals

from celery.utils.imports import qualname

from testapp.models import Article, Tag

from .base import WebhookSuite, event_url, testcase

EVENT1_REF = 'hardcoded1'
EVENT1_URL = event_url('article.changed', ref=EVENT1_REF)
EVENT2_REF = 'hardcoded2'
EVENT2_URL = event_url('article.changed', ref=EVENT2_REF)


def callback_subscribers(event, sender=None, **kwargs):
    return [
        EVENT1_URL,
        EVENT2_URL,
    ]


class Default(WebhookSuite):

    @testcase('all', iterations=1)
    def endpoints(self):
        sub1 = self.subscribe('article.created')
        sub2 = self.subscribe('article.changed')
        subs = self.list_subscriptions()
        assert sub1 in subs
        assert sub2 in subs
        self.unsubscribe(sub1['subscription'])
        subs2 = self.list_subscriptions()
        assert sub1 not in subs2
        assert sub2 in subs2
        self.unsubscribe(sub2['subscription'])
        subs3 = self.list_subscriptions()
        assert sub1 not in subs3
        assert sub2 not in subs3

    @testcase('all', iterations=1)
    def subscribe_to_article_created(self, event='article.created'):
        sub = self.subscribe('article.created')
        article = self.create_article('The quick brown fox')
        self.assert_article_event_received(article, event, sub)

    @testcase('all', iterations=1)
    def subscribe_to_article_changed(self, event='article.changed'):
        article = self.create_article('The quick brown fox')
        sub = self.subscribe(event)
        article = Article.objects.filter(author=self.user)[0]
        article.title = 'The lazy dog'
        article.save()
        self.assert_article_event_received(article, event, sub)

    @testcase('all', iterations=1)
    def subscribe_to_article_published(self, event='article.published'):
        article = self.create_article('The quick brown fox')
        sub = self.subscribe(event)
        article.state = 'PUBLISHED'
        article.save()
        self.assert_article_event_received(article, event, sub)

    @testcase('all', iterations=1)
    def subscribe_to_article_removed(self, event='article.removed'):
        article = self.create_article('The quick brown fox')
        sub = self.subscribe(event)
        rev = self.reverse_article(article)
        article.delete()
        self.assert_article_event_received(article, event, sub, reverse=rev)

    @testcase('all', iterations=1)
    def subscribe_to_tag_added(self, event='article.tag_added'):
        article = self.create_article('The quick brown fox')
        tag, _ = Tag.objects.get_or_create(name='kids')
        sub = self.subscribe(event)
        article.tags.add(tag)
        self.assert_article_event_received(article, event, sub)

    @testcase('all', iterations=1)
    def subscribe_to_tag_removed(self, event='article.tag_removed'):
        article = self.create_article('The quick brown fox')
        tag, _ = Tag.objects.get_or_create(name='kids')
        article.tags.add(tag)
        sub = self.subscribe(event)
        article.tags.remove(tag)
        self.assert_article_event_received(article, event, sub)

    @testcase('all', iterations=1)
    def subscribe_to_tag_all_cleared(self, event='article.tag_all_cleared'):
        article = self.create_article('The quick brown fox')
        tag1, _ = Tag.objects.get_or_create(name='kids')
        tag2, _ = Tag.objects.get_or_create(name='fun')
        article.tags.add(tag1)
        article.tags.add(tag2)
        sub = self.subscribe(event)
        article.tags.clear()
        self.assert_article_event_received(article, event, sub)

    @testcase('all', iterations=5)
    def hundred_subscribers(self, event='article.created'):
        subs = [
            self.subscribe(event, rest='&n={0}'.format(str(i)))
            for i in range(100)
        ]
        article = self.create_article('The Boring Bear')
        self.assert_article_event_received(article, event, subs[0], n=100)

    @testcase('all', iterations=1)
    def sender_mismatch_does_not_dispatch(self, event='article.changed'):
        self.token = self._login('test2', 'test2')
        article = self.create_article('The Boring Bear')
        self.subscribe(event)
        article.title = 'The Mighty Duck'
        article.save()
        self.assert_webhook_not_received()

    @testcase('all', iterations=1)
    def unsubscribe_does_not_dispatch(self, event='article.created'):
        sub = self.subscribe(event)
        article = self.create_article('Angry Bots')
        self.assert_article_event_received(article, event, sub)
        self.unsubscribe(sub['subscription'])
        self.create_article('Funky Bots')
        self.assert_webhook_not_received()

    @testcase('all', iterations=1)
    def subscriber_setting(self, event='article.changed'):
        with self.worker_subscribe_to(
                'article.changed', url=self._event_url(event)):
            article = self.create_article('Lazy Babies')
            article.title = 'Hazy Babies'
            article.save()
            self.assert_article_event_received(article, event)

    @testcase('all', iterations=1)
    def subscriber_callback_setting(self, event='article.changed'):
        with self.worker_subscribe_to(
                'article.changed', callback=qualname(callback_subscribers)):
            article = self.create_article('A brown fox')
            article.title = 'A red fox'
            article.save()
            self.assert_article_event_received(article, event, ref=EVENT1_REF)
            self.assert_article_event_received(article, event, ref=EVENT2_REF)
