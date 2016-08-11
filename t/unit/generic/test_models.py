from __future__ import absolute_import, unicode_literals

from case import Mock

from thorn.generic.models import SubscriberModelMixin


def test_sign(patching, message='thequickbrownfox'):
    sign = patching('thorn.utils.hmac.sign')
    patching('thorn.utils.hmac.hashlib')
    x = SubscriberModelMixin()
    x.hmac_secret = Mock(name='hmac_secret')
    x.hmac_digest = 'sha1'
    assert x.sign(message) is sign.return_value
    sign.assert_called_with(x.hmac_digest, x.hmac_secret, message)
