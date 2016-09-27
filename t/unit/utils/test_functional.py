from __future__ import absolute_import, unicode_literals

import pytest

from case import Mock, patch

from thorn.utils.functional import Q, chunks, traverse_subscribers


@pytest.mark.parametrize('max,input,expected', [
    (2, range(10), [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]),
    (2, range(9), [[0, 1], [2, 3], [4, 5], [6, 7], [8]]),
])
def test_chunks(max, input, expected):
    assert list(chunks(iter(input), max)) == expected


class test_Q:

    def test_missing_op(self):
        with pytest.raises(ValueError):
            Q(foo=30)(Mock())

    def test_missing_op__nested(self):
        with pytest.raises(ValueError):
            Q(foo__bar__baz=30)(Mock())

    def test_missing_attr(self):
        with pytest.raises(AttributeError):
            Q(foo__eq=30)(object())

    def test_eq(self):
        assert Q(foo__eq=30)(Mock(foo=30))

        assert not Q(foo__eq=30)(Mock(foo=10))
        assert not Q(foo__eq=30)(Mock(foo=None))

    def test_eq__True(self):
        assert Q(foo__eq=True)(Mock(foo=True))
        assert Q(foo__eq=True)(Mock(foo=30))
        assert Q(foo__eq=True)(Mock(foo='foo'))

        assert not Q(foo__eq=True)(Mock(foo=''))
        assert not Q(foo__eq=True)(Mock(foo=None))
        assert not Q(foo__eq=True)(Mock(foo=0))

    def test_eq__False(self):
        assert not Q(foo__eq=False)(Mock(foo=True))
        assert not Q(foo__eq=False)(Mock(foo=30))
        assert not Q(foo__eq=False)(Mock(foo='foo'))

        assert Q(foo__eq=False)(Mock(foo=''))
        assert Q(foo__eq=False)(Mock(foo=None))
        assert Q(foo__eq=False)(Mock(foo=0))

    def test_ne(self):
        assert Q(foo__ne=30)(Mock(foo=20))
        assert Q(foo__ne=30)(Mock(foo=None))

        assert not Q(foo__ne=30)(Mock(foo=30))

    def test_gt(self):
        assert Q(foo__gt=30)(Mock(foo=31))

        assert not Q(foo__gt=30)(Mock(foo=30))

    def test_gte(self):
        assert Q(foo__gte=30)(Mock(foo=31))
        assert Q(foo__gte=30)(Mock(foo=30))

        assert not Q(foo__gte=30)(Mock(foo=29))

    def test_lt(self):
        assert Q(foo__lt=30)(Mock(foo=29))

        assert not Q(foo__lt=30)(Mock(foo=30))

    def test_lte(self):
        assert Q(foo__lte=30)(Mock(foo=29))
        assert Q(foo__lte=30)(Mock(foo=30))

        assert not Q(foo__lte=30)(Mock(foo=31))

    def test_contains(self):
        assert Q(foo__contains='_')(Mock(foo='the_quick'))
        assert not Q(foo__contains='_')(Mock(foo='the!quick'))

    def test_startswith(self):
        assert Q(foo__startswith='_')(Mock(foo='_the_quick'))
        assert not Q(foo__startswith='_')(Mock(foo='!the!quick'))

    def test_endswith(self):
        assert Q(foo__endswith='_')(Mock(foo='the_quick_'))
        assert not Q(foo__endswith='_')(Mock(foo='the!quick!'))

    def test_is(self):
        obj = object()
        assert Q(foo__is=None)(Mock(foo=None))
        assert Q(foo__is=obj)(Mock(foo=obj))
        assert not Q(foo__is=None)(Mock(foo=0))
        assert not Q(foo__is=obj)(Mock(foo=object()))

    def test_is_not(self):
        obj = object()
        assert Q(foo__is_not=None)(Mock(foo=0))
        assert Q(foo__is_not=obj)(Mock(foo=object()))
        assert not Q(foo__is_not=None)(Mock(foo=None))
        assert not Q(foo__is_not=obj)(Mock(foo=obj))

    def test_nested_fields(self):
        obj = Mock(
            author=Mock(
                full_name='George Costanza',
                is_staff=True,
                rank=3.03,
                violations=None,
            ),
            tags=['abc', 'def', 'ghi'],
        )
        assert Q(
            author__is_staff__eq=True,
            author__full_name__contains=' ',
            author__full_name__startswith='George',
            author__full_name__endswith='Costanza',
            author__rank__gt=2.3,
            author__violations__is=None,
            tags__contains='abc',
        )(obj)
        assert not Q(
            author__is_staff__eq=True,
            author__full_name__contains=' ',
            author__full_name__startswith='George',
            author__full_name__endswith='Costanza',
            author__rank__gt=2.3,
            author__violations__is=None,
            tags__contains='zzz',
        )(obj)
        assert not Q(
            author__is_staff__eq=False,
            author__full_name__contains=' ',
            author__full_name__startswith='George',
            author__full_name__endswith='Costanza',
            author__rank__gt=2.3,
            author__violations__is=None,
        )(obj)

    def test_all_must_match(self):
        obj = Mock(
            full_name='George Costanza',
            is_staff=True,
            rank=3.03,
            violations=None,
        )
        assert Q(
            is_staff__eq=True,
            full_name__contains=' ',
            full_name__startswith='George',
            full_name__endswith='Costanza',
            rank__gt=2.3,
            violations__is=None,
        )(obj)
        assert not Q(
            is_staff__eq=False,
            full_name__contains=' ',
            full_name__startswith='George',
            full_name__endswith='Costanza',
            rank__gt=2.3,
            violations__is=None,
        )(obj)

    def test_nested_Q_objects(self):
        x = Mock(foo=Mock(bar=1, baz=2))
        q1 = Q(Q(foo__x__eq=True), foo__bar__eq=1) & Q(foo__baz__eq=2)
        q2 = Q(foo__bar__eq=1) & Q(foo__baz__eq=3)
        q3 = Q(foo__baz__eq=3) | Q(foo__bar__eq=1)
        q4 = Q(foo__bar__eq=1) & Q(Q(foo__x__ne=True), foo__baz__eq=2)
        assert q1(x)
        assert not q2(x)
        assert (~q2)(x)

        assert q3(x)
        assert not q4(x)

    def test_now_eq__no_previous_version(self):
        class X(object):
            foo = 1
        q = Q(foo__now_eq=1)
        assert q(X())

    def test_now_eq(self):
        x1 = Mock(foo=Mock(bar=1, baz=2))
        x1._previous_version = Mock(foo=Mock(bar=0, baz=2))
        q = Q(foo__bar__now_eq=1)
        assert q(x1)

        x2 = Mock(foo=Mock(bar=1, baz=2))
        x2._previous_version = Mock(foo=Mock(bar=1, baz=2))
        assert not q(x2)

        x3 = Mock(state1='PUBLISHED', state2='PUBLISHED')
        x3._previous_version = Mock(
            state1='PENDING', state2='PUBLISHED',
        )
        assert Q(state1__now_eq='PUBLISHED')(x3)
        assert not Q(state2__now_eq='PUBLISHED')(x3)

    def test_now_ne(self):
        x1 = Mock(foo=Mock(bar=1, baz=1))
        x1._previous_version = Mock(foo=Mock(bar=0, baz=2))
        assert Q(foo__bar__now_ne=2)(x1)
        assert not Q(foo__baz__now_ne=2)(x1)

    def test_now_gt(self):
        x1 = Mock(foo=Mock(bar=22, baz=22))
        x1._previous_version = Mock(foo=Mock(bar=10, baz=42))
        assert Q(foo__bar__now_gt=20)(x1)
        assert not Q(foo__baz__now_gt=20)(x1)

    def test_now_lt(self):
        x1 = Mock(foo=Mock(bar=22, baz=22))
        x1._previous_version = Mock(foo=Mock(bar=42, baz=12))
        assert Q(foo__bar__now_lt=40)(x1)
        assert not Q(foo__baz__now_lt=40)(x1)

    def test_now_gte(self):
        x1 = Mock(foo=Mock(bar=22, baz=22))
        x1._previous_version = Mock(foo=Mock(bar=22, baz=42))
        assert Q(foo__bar__now_gte=22)(x1)
        assert not Q(foo__baz__now_gte=22)(x1)

    def test_now_lte(self):
        x1 = Mock(foo=Mock(bar=22, baz=22))
        x1._previous_version = Mock(foo=Mock(bar=42, baz=12))
        assert Q(foo__bar__now_lte=22)(x1)
        assert not Q(foo__baz__now_lte=22)(x1)

    def test_now_is(self):
        x1 = Mock(foo=Mock(bar=None, baz=None))
        x1._previous_version = Mock(foo=Mock(bar=30, baz=None))
        assert Q(foo__bar__now_is=None)(x1)
        assert not Q(foo__baz__now_is=None)(x1)

    def test_now_is_not(self):
        x1 = Mock(foo=Mock(bar=30, baz=30))
        x1._previous_version = Mock(foo=Mock(bar=None, baz=10))
        assert Q(foo__bar__now_is_not=None)(x1)
        assert not Q(foo__baz__now_is_not=None)(x1)

    def test_now_contains(self):
        x1 = Mock(foo=Mock(
            bar='The quick brown fox',
            baz='The quick brown fox'),
        )
        x1._previous_version = Mock(foo=Mock(
            bar='The quick red fox',
            baz='The quick brown fox',
        ))
        assert Q(foo__bar__now_contains='brown')(x1)
        assert not Q(foo__baz__now_contains='brown')(x1)

    def test_now_startswith(self):
        x1 = Mock(foo=Mock(
            bar='The quick brown fox',
            baz='The quick brown fox',
        ))
        x1._previous_version = Mock(foo=Mock(
            bar='The lazy brown fox',
            baz='The quick brown fox',
        ))
        assert Q(foo__bar__now_startswith='The quick')(x1)
        assert not Q(foo__baz__now_startswith='The quick')(x1)

    def test_now_endswith(self):
        x1 = Mock(foo=Mock(
            bar='The quick brown fox',
            baz='The quick brown fox',
        ))
        x1._previous_version = Mock(foo=Mock(
            bar='The lazy red fox',
            baz='The lazy brown fox',
        ))
        assert Q(foo__bar__now_endswith='brown fox')(x1)
        assert not Q(foo__baz__now_endswith='brown fox')(x1)

    def test_in(self):
        x1 = Mock(foo=Mock(
            bar='PUBLISHED',
            baz='PENDING',
        ))
        assert Q(foo__bar__in={'PUBLISHED', 'X', 'Y', 'Z'})(x1)
        assert not Q(foo__baz__in={'PUBLISHED', 'X', 'Y', 'Z'})(x1)

    def test_now_in(self):
        x1 = Mock(foo=Mock(
            bar='PUBLISHED',
            baz='PUBLISHED',
        ))
        x1._previous_version = Mock(foo=Mock(
            bar='PENDING',
            baz='PUBLISHED',
        ))
        assert Q(foo__bar__now_in={'PUBLISHED', 'X', 'Y', 'Z'})(x1)
        assert not Q(foo__baz__now_in={'PUBLISHED', 'X', 'Y', 'Z'})(x1)

    def test_not_in(self):
        x1 = Mock(foo=Mock(
            bar='PUBLISHED',
            baz='PENDING',
        ))
        assert Q(foo__bar__not_in={'PENDING', 'X', 'Y', 'Z'})(x1)
        assert not Q(foo__baz__not_in={'PENDING', 'X', 'Y', 'Z'})(x1)

    def test_now_not_in(self):
        x1 = Mock(foo=Mock(
            bar='PUBLISHED',
            baz='PUBLISHED',
        ))
        x1._previous_version = Mock(foo=Mock(
            bar='PENDING',
            baz='PUBLISHED',
        ))
        assert Q(foo__bar__now_not_in={'PENDING', 'X', 'Y', 'Z'})(x1)
        assert not Q(foo__baz__now_not_in={'PENDING', 'X', 'Y', 'Z'})(x1)


class test_traverse_subscribers:

    @patch('thorn.utils.functional.symbol_by_name')
    def test_symbol_string(self, symbol_by_name):
        symbol_by_name.return_value = 'http://e.com'
        x = [1, 2, ['!some.where.symbol', 3, 4], 5, 6]
        assert list(traverse_subscribers(x)) == [
            1, 2, 5, 6, symbol_by_name.return_value, 3, 4
        ]
        symbol_by_name.assert_called_once_with('some.where.symbol')

    def test_none_items(self):
        assert list(traverse_subscribers([None, [None], None])) == []
