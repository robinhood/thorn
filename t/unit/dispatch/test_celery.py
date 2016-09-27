from __future__ import absolute_import, unicode_literals

from case import ANY, Mock, call, patch

from thorn.dispatch.celery import Dispatcher, WorkerDispatcher
from thorn.request import Request


class test_Dispatcher:

    def test_send(self, patching):
        send_event = patching('thorn.dispatch.celery.send_event')
        event = Mock(name='event')
        payload = Mock(name='payload')
        user = Mock(name='user')
        context = {'instance': 9}
        res = Dispatcher().send(
            event, payload, user, timeout=3.03, kw=9, context=context)
        send_event.s.assert_called_once_with(
            event, payload, user.pk, 3.03, context,
        )
        send_event.s().apply_async.assert_called_once_with()
        assert res is send_event.s().apply_async()

    @patch('thorn.dispatch.celery.group')
    def test_flush_buffer(self, group, app):
        g = [None]

        subscriber = Mock(name='subscriber')
        subscriber.url = 'http://example.com/?e=1'

        def group_consume_generator(arg):
            g[0] = list(arg)
            return group.return_value
        group.side_effect = group_consume_generator

        d = Dispatcher()
        d.pending_outbound.extend(
            Request('order.created', {}, None, subscriber)
            for i in range(100)
        )
        d.flush_buffer()
        assert g[0]
        assert len(g[0]) == 100 / app.settings.THORN_CHUNKSIZE
        group.return_value.delay.assert_called_once_with()
        assert not d.pending_outbound


class test_WorkerDispatcher:

    def setup(self):
        self.app = Mock(name='app')
        self.dispatcher = WorkerDispatcher(app=self.app)

    def test_send(self, patching):
        group = patching('thorn.dispatch.celery.group')
        dispatch_requests = patching('thorn.dispatch.celery.dispatch_requests')

        def eval_genexp(x):
            list(x)
            return group.return_value
        group.side_effect = eval_genexp
        reqs = [Mock(name='r1'), Mock(name='r2'), Mock(name='r2')]
        self.dispatcher.prepare_requests = Mock(name='prepare_requests')
        self.dispatcher.prepare_requests.return_value = reqs
        self.dispatcher.group_requests = Mock(name='group_requests')
        self.dispatcher.group_requests.return_value = [
            [r] for r in reqs
        ]
        self.dispatcher.send(Mock(), Mock(), Mock(), Mock())
        dispatch_requests.s.assert_has_calls([
            call([req.as_dict()]) for req in reqs
        ])

    def test_group_requests(self, patching):
        chunks = patching('thorn.dispatch.celery.chunks')
        reqs = [Mock(name='r1'), Mock(name='r2'), Mock(name='r3')]
        ret = self.dispatcher.group_requests(reqs)
        chunks.assert_called_with(
            ANY, self.app.settings.THORN_CHUNKSIZE)
        assert ret is chunks()

    def test_compare_requests(self):
        a = Mock(name='r1')
        a.urlident = 'foo'
        b = Mock(name='r2')
        b.urlident = 'bar'
        assert self.dispatcher._compare_requests(a, a)
        assert not self.dispatcher._compare_requests(a, b)
