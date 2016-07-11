from __future__ import absolute_import, unicode_literals

from thorn.utils import hmac
from thorn.utils.compat import bytes_if_py3, to_bytes

from thorn.tests.case import Case, DigestCase, Mock, patch


class test_get_digest(DigestCase):

    def test_get_digest(self):
        self.assertIs(hmac.get_digest('sha1'), self.hashlib.sha1)


class test_sign(DigestCase):

    @patch('base64.b64encode')
    @patch('hmac.new')
    def test_sign(self, hmac_new, b64encode,
                  digest="sha1", key="KEY", msg="MSG"):
        ret = hmac.sign(digest, key, msg)
        hmac_new.assert_called_with(
            bytes_if_py3(key), bytes_if_py3(msg),
            digestmod=hmac.get_digest(digest),
        )
        hmac_new().digest.assert_called_with()
        b64encode.assert_called_with(hmac_new().digest())
        self.assertIs(ret, b64encode())


class test_verify(Case):

    @patch('thorn.utils.hmac.sign')
    @patch('hmac.compare_digest')
    def test_unit(self, compare_digest, sign,
                  digest_method="sha256", key="KEY", msg="MSG"):
        ret = hmac.verify("verify", digest_method, key, msg)
        sign.assert_called_with(digest_method, key, msg)
        compare_digest.assert_called_with(sign(), to_bytes("verify"))
        self.assertIs(ret, compare_digest())

    def test_functional(self, key="KEY", msg="MSG"):
        self.assertTrue(hmac.verify(
            hmac.sign("sha512", key, msg), "sha512", key, msg,
        ))
        self.assertTrue(hmac.verify(
            hmac.sign("sha512", key, msg), "sha512", b"KEY", msg,
        ))
        self.assertFalse(hmac.verify(
            hmac.sign("sha512", key, msg), "sha512", "NKEY", msg,
        ))
        self.assertFalse(hmac.verify(
            hmac.sign("sha512", key, msg), "sha256", "NKEY", msg,
        ))


class test_compat_sign(Case):

    @patch('itsdangerous.Signer')
    @patch('thorn.utils.hmac.get_digest')
    def test(self, get_digest, Signer):
        digest = Mock(name='digest')
        key = Mock(name='key')
        message = Mock(name='message')
        ret = hmac.compat_sign(digest, key, message)
        get_digest.assert_called_with(digest)
        Signer.assert_called_with(key, digest_method=get_digest())
        Signer().get_signature.assert_called_with(message)
        self.assertIs(ret, Signer().get_signature())
