from __future__ import absolute_import, unicode_literals

import pytest

from case import Mock, call

from thorn.dispatch.celery import Dispatcher, WorkerDispatcher


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


class test_WorkerDispatcher:

    @pytest.fixture(autouse=True, scope='function')
    def setup_self(self):
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
        groupbymax = patching('thorn.dispatch.celery.groupbymax')
        reqs = [Mock(name='r1'), Mock(name='r2'), Mock(name='r3')]
        ret = self.dispatcher.group_requests(reqs)
        groupbymax.assert_called_with(
            reqs,
            max=self.app.settings.THORN_CHUNKSIZE,
            key=self.dispatcher._compare_requests,
        )
        assert ret is groupbymax()

    def test_compare_requests(self):
        a = Mock(name='r1')
        a.urlident = 'foo'
        b = Mock(name='r2')
        b.urlident = 'bar'
        assert self.dispatcher._compare_requests(a, a)
        assert not self.dispatcher._compare_requests(a, b)
