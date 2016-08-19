from __future__ import absolute_import, unicode_literals

import pytest

from case import Mock, patch

from thorn.utils import hmac
from thorn.utils.compat import bytes_if_py3, want_bytes


@pytest.fixture()
def hashlib(patching):
    return patching('thorn.utils.hmac.hashlib')


def test_get_digest(hashlib):
    assert hmac.get_digest('sha1') is hashlib.sha1


def test_sign(hashlib, digest="sha1", key="KEY", msg="MSG"):
    with patch('hmac.new') as hmac_new:
        with patch('base64.b64encode') as b64encode:
            ret = hmac.sign(digest, key, msg)
            hmac_new.assert_called_with(
                bytes_if_py3(key), bytes_if_py3(msg),
                digestmod=hmac.get_digest(digest),
            )
            hmac_new().digest.assert_called_with()
            b64encode.assert_called_with(hmac_new().digest())
            assert ret is b64encode()


class test_verify:

    @patch('thorn.utils.hmac.sign')
    @patch('hmac.compare_digest')
    def test_unit(self, compare_digest, sign,
                  digest_method="sha256", key="KEY", msg="MSG"):
        ret = hmac.verify("verify", digest_method, key, msg)
        sign.assert_called_with(digest_method, key, msg)
        compare_digest.assert_called_with(sign(), want_bytes("verify"))
        assert ret is compare_digest()

    def test_functional(self, key="KEY", msg="MSG"):
        assert hmac.verify(
            hmac.sign("sha512", key, msg), "sha512", key, msg)
        assert hmac.verify(
            hmac.sign("sha512", key, msg), "sha512", b"KEY", msg)
        assert not hmac.verify(
            hmac.sign("sha512", key, msg), "sha512", "NKEY", msg)
        assert not hmac.verify(
            hmac.sign("sha512", key, msg), "sha256", "NKEY", msg)


def test_compat_sign():
    with patch('itsdangerous.Signer') as Signer:
        with patch('thorn.utils.hmac.get_digest') as get_digest:
            digest = Mock(name='digest')
            key = Mock(name='key')
            message = Mock(name='message')
            ret = hmac.compat_sign(digest, key, message)
            get_digest.assert_called_with(digest)
            Signer.assert_called_with(key, digest_method=get_digest())
            Signer().get_signature.assert_called_with(message)
            assert ret is Signer().get_signature()
