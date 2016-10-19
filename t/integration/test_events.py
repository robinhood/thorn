from __future__ import absolute_import, unicode_literals
from celery.utils.imports import qualname
from testapp.models import Article, Tag


class test_events:

    def test_endpoints(self, manager):
        sub1 = manager.subscribe('article.created')
        sub2 = manager.subscribe('article.changed')
        subs = manager.list_subscriptions()
        assert sub1 in subs
        assert sub2 in subs
        manager.unsubscribe(sub1['subscription'])
        subs2 = manager.list_subscriptions()
        assert sub1 not in subs2
        assert sub2 in subs2
        manager.unsubscribe(sub2['subscription'])
        subs3 = manager.list_subscriptions()
        assert sub1 not in subs3
        assert sub2 not in subs3

    def test_subscribe_to_article_created(self, manager,
                                          event='article.created'):
        sub = manager.subscribe('article.created')
        article = manager.create_article('The quick brown fox')
        manager.assert_article_event_received(article, event, sub)

    def test_subscribe_to_article_changed(self, manager,
                                          event='article.changed'):
        article = manager.create_article('The quick brown fox')
        sub = manager.subscribe(event)
        article = Article.objects.filter(author=manager.user)[0]
        article.title = 'The lazy dog'
        article.save()
        manager.assert_article_event_received(article, event, sub)

    def test_subscribe_to_article_published(self, manager,
                                            event='article.published'):
        article = manager.create_article('The quick brown fox')
        sub = manager.subscribe(event)
        article.state = 'PUBLISHED'
        article.save()
        manager.assert_article_event_received(article, event, sub)

    def test_subscribe_to_article_removed(self, manager,
                                          event='article.removed'):
        article = manager.create_article('The quick brown fox')
        sub = manager.subscribe(event)
        rev = manager.reverse_article(article)
        article.delete()
        manager.assert_article_event_received(article, event, sub, reverse=rev)

    def test_subscribe_to_tag_added(self, manager, event='article.tag_added'):
        article = manager.create_article('The quick brown fox')
        tag, _ = Tag.objects.get_or_create(name='kids')
        sub = manager.subscribe(event)
        article.tags.add(tag)
        manager.assert_article_event_received(article, event, sub)

    def test_subscribe_to_tag_removed(self, manager,
                                      event='article.tag_removed'):
        article = manager.create_article('The quick brown fox')
        tag, _ = Tag.objects.get_or_create(name='kids')
        article.tags.add(tag)
        sub = manager.subscribe(event)
        article.tags.remove(tag)
        manager.assert_article_event_received(article, event, sub)

    def test_subscribe_to_tag_all_cleared(self, manager,
                                          event='article.tag_all_cleared'):
        article = manager.create_article('The quick brown fox')
        tag1, _ = Tag.objects.get_or_create(name='kids')
        tag2, _ = Tag.objects.get_or_create(name='fun')
        article.tags.add(tag1)
        article.tags.add(tag2)
        sub = manager.subscribe(event)
        article.tags.clear()
        manager.assert_article_event_received(article, event, sub)

    def test_hundred_subscribers(self, manager, event='article.created'):
        subs = [
            manager.subscribe(event, rest='&n={0}'.format(str(i)))
            for i in range(100)
        ]
        article = manager.create_article('The Boring Bear')
        manager.assert_article_event_received(article, event, subs[0], n=100)

    def test_sender_mismatch_does_not_dispatch(self, manager,
                                               event='article.changed'):
        self.token = manager._login('test2', 'test2')
        article = manager.create_article('The Boring Bear')
        manager.subscribe(event)
        article.title = 'The Mighty Duck'
        article.save()
        manager.assert_webhook_not_received()

    def test_unsubscribe_does_not_dispatch(self, manager,
                                           event='article.created'):
        sub = manager.subscribe(event)
        article = manager.create_article('Angry Bots')
        manager.assert_article_event_received(article, event, sub)
        manager.unsubscribe(sub['subscription'])
        manager.create_article('Funky Bots')
        manager.assert_webhook_not_received()

    def xxx_subscriber_setting(self, manager, event='article.changed'):
        with manager.worker_subscribe_to(
                'article.changed', url=manager.event_url(event)):
            article = manager.create_article('Lazy Babies')
            article.title = 'Hazy Babies'
            article.save()
            manager.assert_article_event_received(article, event)

    def xxx_subscriber_callback_setting(self, manager,
                                        event='article.changed'):
        event1_ref = 'hardcoded1'
        event1_url = manager.event_url('article.changed', ref=event1_ref)
        event2_ref = 'hardcoded2'
        event2_url = manager.event_url('article.changed', ref=event2_ref)

        def callback_subscribers(event, sender=None, **kwargs):
            return [
                event1_url,
                event2_url,
            ]

        with manager.worker_subscribe_to(
                'article.changed', callback=qualname(callback_subscribers)):
            article = manager.create_article('A brown fox')
            article.title = 'A red fox'
            article.save()
            manager.assert_article_event_received(
                article, event, ref=event1_ref)
            manager.assert_article_event_received(
                article, event, ref=event2_ref)
