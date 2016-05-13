"""

    thorn.utils.json
    ================

    Json serialization utilities.

"""
from __future__ import absolute_import, unicode_literals

import datetime
import decimal
import uuid

from six import text_type

from celery.utils.imports import symbol_by_name

try:
    from django.utils.functional import Promise as DjangoPromise
except ImportError:  # pragma: no cover
    class DjangoPromise(object):  # noqa
        pass

__all__ = ['JsonEncoder', 'dumps']


def get_best_json(attr=None,
                  choices=['kombu.utils.json', 'simplejson', 'json']):
    for i, module in enumerate(choices):
        try:
            return symbol_by_name(
                ':'.join([module, attr]) if attr else module
            )
        except (AttributeError, ImportError):
            if i + 1 >= len(choices):
                raise
json = get_best_json()


class JsonEncoder(get_best_json('JSONEncoder')):
    # like django.core.serializers.json.JSONEncoder but preserves
    # datetime microsecond information.

    def default(self, o,
                dates=(datetime.datetime, datetime.date),
                times=(datetime.time,),
                textual=(decimal.Decimal, uuid.UUID, DjangoPromise),
                isinstance=isinstance,
                datetime=datetime.datetime,
                text_type=text_type):
        if isinstance(o, dates):
            if not isinstance(o, datetime):
                o = datetime(o.year, o.month, o.day, 0, 0, 0, 0)
            r = o.isoformat()
            if r.endswith("+00:00"):
                r = r[:-6] + "Z"
            return r
        elif isinstance(o, times):
            return o.isoformat()
        elif isinstance(o, textual):
            return text_type(o)
        else:
            return super(JsonEncoder, self).default(o)


def dumps(obj, encode=json.dumps, cls=JsonEncoder):
    return encode(obj, cls=cls)
