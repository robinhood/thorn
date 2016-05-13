from __future__ import absolute_import, unicode_literals

from thorn.dispatch.celery import Dispatcher, WorkerDispatcher

from thorn.tests.case import Case, Mock, call, patch


class test_Dispatcher(Case):

    @patch('thorn.dispatch.celery.send_event')
    def test_send(self, send_event):
        event = Mock(name='event')
        payload = Mock(name='payload')
        user = Mock(name='user')
        res = Dispatcher().send(event, payload, user, timeout=3.03, kw=9)
        send_event.s.assert_called_once_with(
            event, payload, user.pk, 3.03,
        )
        send_event.s().apply_async.assert_called_once_with()
        self.assertIs(res, send_event.s().apply_async())


class test_WorkerDispatcher(Case):

    def setUp(self):
        self.app = Mock(name='app')
        self.dispatcher = WorkerDispatcher(app=self.app)

    @patch('thorn.dispatch.celery.dispatch_requests')
    @patch('thorn.dispatch.celery.group')
    def test_send(self, group, dispatch_requests):
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

    @patch('thorn.dispatch.celery.groupbymax')
    def test_group_requests(self, groupbymax):
        reqs = [Mock(name='r1'), Mock(name='r2'), Mock(name='r3')]
        ret = self.dispatcher.group_requests(reqs)
        groupbymax.assert_called_with(
            reqs,
            max=self.app.settings.THORN_CHUNKSIZE,
            key=self.dispatcher._compare_requests,
        )
        self.assertIs(ret, groupbymax())

    def test_compare_requests(self):
        a = Mock(name='r1')
        a.urlident = 'foo'
        b = Mock(name='r2')
        b.urlident = 'bar'
        self.assertTrue(self.dispatcher._compare_requests(a, a))
        self.assertFalse(self.dispatcher._compare_requests(a, b))
