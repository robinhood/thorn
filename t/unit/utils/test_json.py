from __future__ import absolute_import, unicode_literals

import pytest
import pytz

from decimal import Decimal
from datetime import datetime
from json import loads
from six import text_type
from uuid import uuid4

from case import Mock, mock, patch

from thorn.utils.json import dumps, get_best_json


def test_encode_datetime():
    now = datetime.utcnow()
    now_utc = now.replace(tzinfo=pytz.utc)
    stripped = datetime(*now.timetuple()[:3])
    serialized = loads(dumps({
        'datetime': now,
        'tz': now_utc,
        'date': now.date(),
        'time': now.time()},
    ))
    assert serialized == {
        'datetime': now.isoformat(),
        'tz': '{0}Z'.format(now_utc.isoformat().split('+', 1)[0]),
        'time': now.time().isoformat(),
        'date': stripped.isoformat(),
    }


def test_encode_Decimal():
    d = Decimal('3314132.13363235235324234123213213214134')
    assert loads(dumps({'d': d})) == {
        'd': text_type(d),
    }


def test_encode_UUID():
    id = uuid4()
    assert loads(dumps({'u': id})) == {
        'u': text_type(id),
    }


def test_default():
    with pytest.raises(TypeError):
        dumps({'o': object()})


@mock.mask_modules('simplejson')
def test_A_simplejson():
    with mock.reset_modules('thorn.utils.json'):
        from thorn.utils import json
        obj = Mock(name='obj')
        encode = Mock(name='encode')
        assert json.dumps(obj, encode=encode) is encode.return_value
        encode.assert_called_with(obj, cls=json.JsonEncoder)


def test_B_simplejson():
    with mock.module('simplejson'):
        with mock.reset_modules('thorn.utils.json'):
            from thorn.utils import json
            obj = Mock(name='obj')
            encode = Mock(name='encode')
            assert json.dumps(obj, encode=encode) is encode.return_value
            encode.assert_called_with(
                obj, cls=json.JsonEncoder, use_decimal=False)


class test_get_best_json:

    @patch('thorn.utils.json.symbol_by_name')
    def test_no_alternatives(self, symbol_by_name):
        from thorn.utils import json
        symbol_by_name.side_effect = ImportError()
        with pytest.raises(ImportError):
            json.get_best_json()

    def test_no_choices(self):
        get_best_json(choices=[])
