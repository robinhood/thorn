from __future__ import absolute_import, unicode_literals

import pickle
import pytest

from weakref import ref

from case import Mock, call

from thorn.exceptions import BufferNotEmpty
from thorn.dispatch.base import Dispatcher


def subscriber_from_dict(d, event):
    if not isinstance(d, dict):
        d = {'url': d}
    return dict(d, event=event)


class test_Dispatcher:

    def setup(self):
        self._app = Mock(name='app')
        self.dispatcher = Dispatcher(app=self._app)

    def test_dispatch_request(self):
        request = Mock(name='request')
        self.dispatcher.dispatch_request(request)
        request.dispatch.assert_called_with()

    def test_enable_buffer(self):
        assert not self.dispatcher._buffer
        self.dispatcher.enable_buffer()
        assert self.dispatcher._buffer
        self.dispatcher.disable_buffer()
        assert not self.dispatcher._buffer

    def test_disable_buffer__buffer_not_empty(self):
        self.dispatcher.enable_buffer()
        self.dispatcher.pending_outbound.append(32)
        with pytest.raises(BufferNotEmpty):
            self.dispatcher.disable_buffer()

    def test_is_buffer_owner(self):

        class Bunch(object):
            pass
        obj = Bunch()

        # no owner, anyone can flush
        assert self.dispatcher._is_buffer_owner(obj)
        self.dispatcher._buffer_owner = ref(obj)
        assert self.dispatcher._is_buffer_owner(obj)
        assert not self.dispatcher._is_buffer_owner(Bunch())

    def test_buffering(self):
        self.dispatcher.enable_buffer()
        assert not self.dispatcher.pending_outbound
        req = Mock(name='req1')
        self.dispatcher.dispatch_request(req)
        req.dispatch.assert_not_called()
        assert req in self.dispatcher.pending_outbound
        req2 = Mock(name='req2')
        self.dispatcher.dispatch_request(req2)
        assert req2 in self.dispatcher.pending_outbound
        req2.dispatch.assert_not_called()
        req.dispatch_assert_not_called()
        self.dispatcher.flush_buffer()
        req.dispatch.assert_called()
        req2.dispatch.assert_called()

    def test_send(self, patching):
        barrier = patching('thorn.dispatch.base.barrier')
        event = Mock(name='event')
        payload = Mock(name='payload')
        sender = Mock(name='sender')
        self.dispatcher.prepare_requests = Mock(name='prepare_requests')
        reqs = self.dispatcher.prepare_requests.return_value = [
            Mock(name='r1'), Mock(name='r2'), Mock(name='r3'),
        ]
        ret = self.dispatcher.send(event, payload, sender, timeout=3.03)
        barrier.assert_called()
        assert ret is barrier.return_value
        for req in reqs:
            req.dispatch.assert_called_with()
        assert barrier.call_args[0][0] == [r.dispatch() for r in reqs]

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
        assert 'A' in cache1
        v1 = cache1['A'] = object()
        assert self.dispatcher.encode_cached('a', cache1, 'A') == v1
        assert self.dispatcher.encode_cached('a', cache2, 'A') == encode()

    def test_encode_payload(self):
        data = Mock(name='data')
        codec = Mock(name='codec')
        self._app.settings.THORN_CODECS = {
            'application/foo': codec,
        }
        assert self.dispatcher.encode_payload(
            data, 'application/x-mooOOO') is data
        assert self.dispatcher.encode_payload(
            data, 'application/foo') is codec.return_value
        codec.assert_called_with(data)

    def test_subscribers_for_event(self):
        source1, source2 = Mock(name='source1'), Mock(name='source2')
        source1.return_value = [1, 2, 3]
        source2.return_value = [4, 5, 6]
        self.dispatcher.subscriber_sources = [source1, source2]
        assert list(self.dispatcher.subscribers_for_event('foo.bar')) == [
            1, 2, 3, 4, 5, 6
        ]

    def test__stored_subscribers(self):
        assert (self.dispatcher._stored_subscribers('foo.bar') is
                self._app.Subscribers.matching.return_value)
        self._app.Subscribers.matching.assert_called_with(
            event='foo.bar', user=None)

    def test_configured_subscribers__string_scalar(self):
        self._app.settings.THORN_SUBSCRIBERS = {
            'foo.bar': 'http://www.example.com/e/',
        }
        self._app.Subscriber.from_dict = subscriber_from_dict
        assert list(self.dispatcher._configured_subscribers('foo.bar')) == [
            dict(event='foo.bar', url='http://www.example.com/e/'),
        ]

    def test_configured_subscribers__callback(self):
        callback1 = Mock(name='callback1')
        callback1.return_value = ['http://a.com/1', 'http://a.com/2']
        callback2 = Mock(name='callback2')
        callback2.return_value = iter(['http://b.com/1', 'http://b.com/2'])
        self._app.settings.THORN_SUBSCRIBERS = {
            'foo.bar': [callback1, callback2],
        }
        self._app.Subscriber.from_dict = subscriber_from_dict
        assert list(self.dispatcher._configured_subscribers('foo.bar')) == [
            dict(event='foo.bar', url='http://a.com/1'),
            dict(event='foo.bar', url='http://a.com/2'),
            dict(event='foo.bar', url='http://b.com/1'),
            dict(event='foo.bar', url='http://b.com/2'),
        ]

    def test_configured_subscribers__string_list(self):
        self._app.settings.THORN_SUBSCRIBERS = {
            'foo.bar': [
                'http://www.example.com/e/a/',
                'http://www.example.com/e/b/',
            ],
        }
        self._app.Subscriber.from_dict = subscriber_from_dict
        assert list(self.dispatcher._configured_subscribers('foo.bar')) == [
            dict(event='foo.bar', url='http://www.example.com/e/a/'),
            dict(event='foo.bar', url='http://www.example.com/e/b/'),
        ]

    def test_configured_subscribers__dict_scalar(self):
        self._app.settings.THORN_SUBSCRIBERS = {
            'foo.bar': {
                'url': 'http://www.example.com/e/',
                'content_type': 'application/x-www-form-urlencoded',
            },
        }
        self._app.Subscriber.from_dict = subscriber_from_dict
        assert list(self.dispatcher._configured_subscribers('foo.bar')) == [
            dict(event='foo.bar',
                 url='http://www.example.com/e/',
                 content_type='application/x-www-form-urlencoded')
        ]

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
        assert list(self.dispatcher._configured_subscribers('foo.bar')) == [
            dict(event='foo.bar',
                 url='http://www.example.com/e/a/',
                 content_type='application/x-www-form-urlencoded'),
            dict(event='foo.bar',
                 url='http://www.example.com/e/b/',
                 content_type='application/json'),
        ]

    def test_reduce(self):
        self.dispatcher.timeout = 303
        d2 = pickle.loads(pickle.dumps(self.dispatcher))
        assert d2.timeout == 303
        assert d2.app is self.app
