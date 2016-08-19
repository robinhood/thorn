from __future__ import absolute_import, unicode_literals

import pytest

from case import Mock

from thorn import _state


class test_current_app:

    def setup_method(self, method):
        self._prev_app, _state.default_app = _state.default_app, None

    def teardown_method(self, method):
        _state.default_app = self._prev_app
        _state._tls.current_app = None

    @pytest.fixture()
    def tls(self, patching):
        return patching('thorn._state._tls')

    def test_when_default(self, patching, tls):
        Thorn = patching('thorn.app.Thorn')
        tls.current_app = None
        assert _state.current_app() is Thorn.return_value
        Thorn.assert_called_once_with()

    def test_when_current(self):
        app = Mock(name='current_app')
        _state.set_current_app(app)
        assert _state.current_app() is app

    def test_when_default_set(self, tls):
        default_app = Mock(name='default_app')
        tls.current_app = None
        _state.set_default_app(default_app)
        assert _state.current_app() is default_app
