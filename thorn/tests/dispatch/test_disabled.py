from __future__ import absolute_import, unicode_literals

from thorn.dispatch.disabled import Dispatcher

from thorn.tests.case import Case


class test_Dispatcher(Case):

    def setUp(self):
        self.dispatcher = Dispatcher()

    def test_send(self):
        self.dispatcher.send(data={'foo': 'bar'})
