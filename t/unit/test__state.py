from __future__ import absolute_import, unicode_literals

import pytest
import thorn

from case import Mock

from thorn import _state


class test_current_app:

    def setup(self):
        self._prev_app, _state.default_app = _state.default_app, None

    def teardown(self):
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


class test_buffer_events:

    def test_context(self):
        app = Mock(name='app')
        _buffer = None

        with thorn.buffer_events(app=app) as buffer:
            _buffer = buffer  # keep alive
            app.enable_buffer.assert_called_once_with(owner=buffer)
        app.flush_buffer.assert_called_once_with(owner=_buffer)
        app.disable_buffer.assert_called_once_with(owner=_buffer)

    def test_explicit_flush(self):
        app = Mock(name='app')
        _buffer = None
        with thorn.buffer_events(app=app) as buffer:
            _buffer = buffer  # keep alive
            app.enable_buffer.assert_called_once_with(owner=buffer)
            buffer.flush()
            app.flush_buffer.assert_called_once_with(owner=None)
            buffer.flush()
            assert app.flush_buffer.call_count == 2
        assert app.flush_buffer.call_count == 3
        app.disable_buffer.assert_called_once_with(owner=_buffer)

    def test_maybe_flush(self):
        app = Mock(name='app')
        with thorn.buffer_events(
                app=app, flush_freq=200, flush_timeout=60.0) as buffer:
            for i in range(30):
                buffer.maybe_flush()
                assert app.flush_buffer.call_count == i
                for j in range(198):
                    buffer.maybe_flush()
                    assert buffer.flush_count == (j + 2) * i or 1
                    assert app.flush_buffer.call_count == i
                buffer.maybe_flush()
                assert buffer.flush_count == 200 * i or 1
                assert app.flush_buffer.call_count == i + 1

    def test_should_flush__timeout(self):
        app = Mock(name='app')
        with thorn.buffer_events(
                app=app, flush_freq=100, flush_timeout=1.0) as buffer:
            buffer.maybe_flush()
            app.flush_buffer.assert_not_called()
            buffer.flush_last -= 1.1
            buffer.maybe_flush()
            app.flush_buffer.assert_called_once_with(owner=None)
            buffer.maybe_flush()
            assert app.flush_buffer.call_count == 1
            buffer.flush_last -= 1.1
            buffer.maybe_flush()
            assert app.flush_buffer.call_count == 2
