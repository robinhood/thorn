from __future__ import absolute_import, unicode_literals

from thorn import _state

from .case import Case, Mock


class test_current_app(Case):

    def setup(self):
        self.Thorn = self.patch('thorn.app.Thorn')
        self.tls = self.patch('thorn._state._tls')
        self.prev_default_app, _state.default_app = _state.default_app, None

    def teardown(self):
        _state.default_app = self.prev_default_app

    def test_when_default(self):
        self.tls.current_app = None
        self.assertIs(_state.current_app(), self.Thorn.return_value)
        self.Thorn.assert_called_once_with()

    def test_when_current(self):
        app = Mock(name='current_app')
        _state.set_current_app(app)
        self.assertIs(_state.current_app(), app)

    def test_when_default_set(self):
        default_app = Mock(name='default_app')
        self.tls.current_app = None
        _state.set_default_app(default_app)
        self.assertIs(_state.current_app(), default_app)
