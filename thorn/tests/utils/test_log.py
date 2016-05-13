from __future__ import absolute_import, unicode_literals

from thorn.utils import log

from thorn.tests.case import Case, patch


class test_get_logger(Case):

    @patch('thorn.utils.log._get_logger')
    def test_sets_parent(self, _get_logger):
        x = log.get_logger(__name__)
        _get_logger.assert_called_with(__name__)
        self.assertIs(x, _get_logger())
        self.assertIs(x.parent, log.base_logger)
