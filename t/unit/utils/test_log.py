from __future__ import absolute_import, unicode_literals

from case import patch

from thorn.utils import log


def test_get_logger_sets_parent():
    with patch('thorn.utils.log._get_logger') as _get_logger:
        x = log.get_logger(__name__)
        _get_logger.assert_called_with(__name__)
        assert x is _get_logger()
        assert x.parent is log.base_logger
