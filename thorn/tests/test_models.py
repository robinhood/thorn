from __future__ import absolute_import, unicode_literals

from thorn.models import SubscriberModelMixin, get_digest

from .case import Case, Mock, patch


class DigestCase(Case):

    def setup(self):
        self.hashlib = self.patch('thorn.models.hashlib')
        self.hashlib.algorithms_available = ['sha1']


class test_get_digest(DigestCase):

    def test_get_digest(self):
        self.assertIs(get_digest('sha1'), self.hashlib.sha1)

    def test_get_digest__algorithm_unavailable(self):
        with self.assertRaises(AssertionError):
            get_digest('sha256')


class test_SubscriberModelMixin(DigestCase):

    @patch('thorn.models.Signer')
    def test_sign(self, Signer):
        x = SubscriberModelMixin()
        x.hmac_secret = Mock(name='hmac_secret')
        x.hmac_digest = 'sha1'
        res = x.sign('thequickbrownfox')
        Signer.assert_called_with(
            x.hmac_secret, digest_method=self.hashlib.sha1,
        )
        Signer().get_signature.assert_called_with('thequickbrownfox')
        self.assertIs(res, Signer().get_signature())
