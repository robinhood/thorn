from __future__ import absolute_import, unicode_literals

from thorn.generic.models import SubscriberModelMixin

from thorn.tests.case import DigestCase, Mock, patch


class test_SubscriberModelMixin(DigestCase):

    @patch('thorn.utils.hmac.sign')
    def test_sign(self, sign, message='thequickbrownfox'):
        x = SubscriberModelMixin()
        x.hmac_secret = Mock(name='hmac_secret')
        x.hmac_digest = 'sha1'
        res = x.sign(message)
        sign.assert_called_with(x.hmac_digest, message, x.hmac_secret)
        self.assertIs(res, sign())
