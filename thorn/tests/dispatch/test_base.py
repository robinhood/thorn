from __future__ import absolute_import, unicode_literals

import pickle

from thorn.dispatch.base import Dispatcher

from thorn.tests.case import Mock, ThornCase, call, patch


def subscriber_from_dict(d, event):
    if not isinstance(d, dict):
        d = {'url': d}
    return dict(d, event=event)


class test_Dispatcher(ThornCase):

    def setup(self):
        self._app = Mock(name='app')
        self.dispatcher = Dispatcher(app=self._app)

    def test_dispatch_request(self):
        request = Mock(name='request')
        self.dispatcher.dispatch_request(request)
        request.dispatch.assert_called_with()

    @patch('thorn.dispatch.base.barrier')
    def test_send(self, barrier):
        event = Mock(name='event')
        payload = Mock(name='payload')
        sender = Mock(name='sender')
        self.dispatcher.prepare_requests = Mock(name='prepare_requests')
        reqs = self.dispatcher.prepare_requests.return_value = [
            Mock(name='r1'), Mock(name='r2'), Mock(name='r3'),
        ]
        ret = self.dispatcher.send(event, payload, sender, timeout=3.03)
        barrier.assert_called()
        self.assertIs(ret, barrier.return_value)
        for req in reqs:
            req.dispatch.assert_called_with()
        self.assertListEqual(
            barrier.call_args[0][0], [r.dispatch() for r in reqs],
        )

    def test_prepare_requests(self):
        event = Mock(name='event')
        event.name = 'foo.bar'
        self.dispatcher.Request = Mock(name='Request')
        self.dispatcher.subscribers_for_event = Mock(name='subscribers')
        targets = self.dispatcher.subscribers_for_event.return_value = [
            Mock(name='r1'), Mock(name='r2'), Mock(name='r3'),
        ]
        targets[0].content_type = 'A'
        targets[1].content_type = 'A'
        targets[2].content_type = 'B'
        codecB = Mock(name='codecB')
        self._app.settings.THORN_CODECS = {'B': codecB}
        list(self.dispatcher.prepare_requests(
            event.name, {'foo': 'bar'}, 501, 30.3, kw=1,
        ))
        self._app.Request.assert_has_calls([
            call(event.name, {'foo': 'bar'}, 501, targets[0],
                 timeout=30.3, kw=1),
            call(event.name, {'foo': 'bar'}, 501, targets[1],
                 timeout=30.3, kw=1),
            call(event.name, codecB(), 501, targets[2],
                 timeout=30.3, kw=1),
        ])

    def test_encode_cached(self):
        cache1, cache2 = {}, {}
        encode = self.dispatcher.encode_payload = Mock(name='encode_cached')

        self.dispatcher.encode_cached('a', cache1, 'A')
        self.assertIn('A', cache1)
        v1 = cache1['A'] = object()
        self.assertEqual(self.dispatcher.encode_cached('a', cache1, 'A'), v1)
        self.assertEqual(
            self.dispatcher.encode_cached('a', cache2, 'A'), encode())

    def test_encode_payload(self):
        data = Mock(name='data')
        codec = Mock(name='codec')
        self._app.settings.THORN_CODECS = {
            'application/foo': codec,
        }
        self.assertIs(
            self.dispatcher.encode_payload(data, 'application/x-mooOOO'), data,
        )
        self.assertIs(
            self.dispatcher.encode_payload(data, 'application/foo'),
            codec.return_value,
        )
        codec.assert_called_with(data)

    def test_subscribers_for_event(self):
        source1, source2 = Mock(name='source1'), Mock(name='source2')
        source1.return_value = [1, 2, 3]
        source2.return_value = [4, 5, 6]
        self.dispatcher.subscriber_sources = [source1, source2]
        self.assertListEqual(
            list(self.dispatcher.subscribers_for_event('foo.bar')),
            [1, 2, 3, 4, 5, 6],
        )

    def test__stored_subscribers(self):
        self.assertIs(
            self.dispatcher._stored_subscribers('foo.bar'),
            self._app.Subscribers.matching.return_value,
        )
        self._app.Subscribers.matching.assert_called_with(
            event='foo.bar', user=None)

    def test_configured_subscribers__string_scalar(self):
        self._app.settings.THORN_SUBSCRIBERS = {
            'foo.bar': 'http://www.example.com/e/',
        }
        self._app.Subscriber.from_dict = subscriber_from_dict
        self.assertListEqual(
            [dict(event='foo.bar', url='http://www.example.com/e/')],
            self.dispatcher._configured_subscribers('foo.bar'),
        )

    def test_configured_subscribers__callback(self):
        callback1 = Mock(name='callback1')
        callback1.return_value = ['http://a.com/1', 'http://a.com/2']
        callback2 = Mock(name='callback2')
        callback2.return_value = iter(['http://b.com/1', 'http://b.com/2'])
        self._app.settings.THORN_SUBSCRIBERS = {
            'foo.bar': [callback1, callback2],
        }
        self._app.Subscriber.from_dict = subscriber_from_dict
        self.assertListEqual(
            [dict(event='foo.bar', url='http://a.com/1'),
             dict(event='foo.bar', url='http://a.com/2'),
             dict(event='foo.bar', url='http://b.com/1'),
             dict(event='foo.bar', url='http://b.com/2')],
            self.dispatcher._configured_subscribers('foo.bar')
        )

    def test_configured_subscribers__string_list(self):
        self._app.settings.THORN_SUBSCRIBERS = {
            'foo.bar': [
                'http://www.example.com/e/a/',
                'http://www.example.com/e/b/',
            ],
        }
        self._app.Subscriber.from_dict = subscriber_from_dict
        self.assertListEqual(
            [dict(event='foo.bar', url='http://www.example.com/e/a/'),
             dict(event='foo.bar', url='http://www.example.com/e/b/')],
            self.dispatcher._configured_subscribers('foo.bar'),
        )

    def test_configured_subscribers__dict_scalar(self):
        self._app.settings.THORN_SUBSCRIBERS = {
            'foo.bar': {
                'url': 'http://www.example.com/e/',
                'content_type': 'application/x-www-form-urlencoded',
            },
        }
        self._app.Subscriber.from_dict = subscriber_from_dict
        self.assertListEqual(
            [dict(event='foo.bar',
                  url='http://www.example.com/e/',
                  content_type='application/x-www-form-urlencoded')],
            self.dispatcher._configured_subscribers('foo.bar'),
        )

    def test_configured_subscribers__dict_list(self):
        self._app.settings.THORN_SUBSCRIBERS = {
            'foo.bar': [
                {'url': 'http://www.example.com/e/a/',
                 'content_type': 'application/x-www-form-urlencoded'},
                {'url': 'http://www.example.com/e/b/',
                 'content_type': 'application/json'},
            ],
        }
        self._app.Subscriber.from_dict = subscriber_from_dict
        self.assertListEqual(
            [dict(event='foo.bar',
                  url='http://www.example.com/e/a/',
                  content_type='application/x-www-form-urlencoded'),
             dict(event='foo.bar',
                  url='http://www.example.com/e/b/',
                  content_type='application/json')],
            self.dispatcher._configured_subscribers('foo.bar'),
        )

    def test_reduce(self):
        self.dispatcher.timeout = 303
        d2 = pickle.loads(pickle.dumps(self.dispatcher))
        self.assertEqual(d2.timeout, 303)
        self.assertIs(d2.app, self.app)
