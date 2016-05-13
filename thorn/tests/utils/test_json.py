from __future__ import absolute_import, unicode_literals

import pytz

from decimal import Decimal
from datetime import datetime
from json import loads
from six import text_type
from uuid import uuid4

from thorn.utils.json import JsonEncoder, dumps, get_best_json

from thorn.tests.case import Case, Mock, patch


class test_JsonEncoder(Case):

    def test_datetime(self):
        now = datetime.utcnow()
        now_utc = now.replace(tzinfo=pytz.utc)
        stripped = datetime(*now.timetuple()[:3])
        serialized = loads(dumps({
            'datetime': now,
            'tz': now_utc,
            'date': now.date(),
            'time': now.time()},
        ))
        self.assertDictEqual(serialized, {
            'datetime': now.isoformat(),
            'tz': '{0}Z'.format(now_utc.isoformat().split('+', 1)[0]),
            'time': now.time().isoformat(),
            'date': stripped.isoformat(),
        })

    def test_Decimal(self):
        d = Decimal('3314132.13363235235324234123213213214134')
        self.assertDictEqual(loads(dumps({'d': d})), {
            'd': text_type(d),
        })

    def test_UUID(self):
        id = uuid4()
        self.assertDictEqual(loads(dumps({'u': id})), {
            'u': text_type(id),
        })

    def test_default(self):
        with self.assertRaises(TypeError):
            dumps({'o': object()})


class test_dumps(Case):

    def test_dumps(self):
        obj = Mock(name='obj')
        encode = Mock(name='encode')
        self.assertIs(dumps(obj, encode=encode), encode.return_value)
        encode.assert_called_with(obj, cls=JsonEncoder)


class test_get_best_json(Case):

    @patch('thorn.utils.json.symbol_by_name')
    def test_no_alternatives(self, symbol_by_name):
        symbol_by_name.side_effect = ImportError()
        with self.assertRaises(ImportError):
            get_best_json()

    def test_no_choices(self):
        get_best_json(choices=[])
