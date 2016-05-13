from __future__ import absolute_import, unicode_literals

from thorn.environment.django import DjangoEnv

from thorn.tests.case import Case, mock, patch


class test_DjangoEnv(Case):
    Env = DjangoEnv

    def setUp(self):
        self.symbol_by_name = self.patch(
            'thorn.environment.django.symbol_by_name',
        )
        self.env = self.Env()

    @mock.environ('DJANGO_SETTINGS_MODULE', '')
    def test_autodetect__when_no_django(self):
        self.assertFalse(self.Env.autodetect())

    @mock.environ('DJANGO_SETTINGS_MODULE', 'proj.settings')
    def test_autodetect__when_django(self):
        self.assertTrue(self.Env.autodetect())

    def test_config(self):
        self.assertIs(self.env.config, self.symbol_by_name.return_value)
        self.symbol_by_name.assert_called_once_with(self.env.settings_cls)

    def test_Subscriber(self):
        self.assertIs(self.env.Subscriber, self.symbol_by_name.return_value)
        self.symbol_by_name.assert_called_once_with(self.env.subscriber_cls)

    def test_Subscribers(self):
        self.assertIs(
            self.env.Subscribers,
            self.symbol_by_name.return_value.objects,
        )
        self.symbol_by_name.assert_called_once_with(self.env.subscriber_cls)

    @patch('importlib.import_module')
    def test_signals(self, import_module):
        self.assertIs(self.env.signals, import_module.return_value)
        import_module.assert_called_with(self.env.signals_cls)

    def test_reverse(self):
        self.assertIs(self.env.reverse, self.symbol_by_name.return_value)
        self.symbol_by_name.assert_called_once_with(self.env.reverse_cls)
