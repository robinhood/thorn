from __future__ import absolute_import, unicode_literals

from thorn.utils.functional import Q, groupbymax

from thorn.tests.case import Case, Mock


class test_groupbymax(Case):

    def test_scalar(self):
        self.assertListEqual(
            list(groupbymax(['a'], 10)), [['a']],
        )

    def test_maxsize(self):
        self.assertListEqual(
            list(groupbymax('aaaabcdde', 3)),
            [['a', 'a', 'a'], ['a'], ['b'], ['c'], ['d', 'd'], ['e']],
        )

    def test_random(self):
        self.assertListEqual(
            list(groupbymax(range(10), 10)),
            [[i] for i in range(10)],
        )

    def test_buf_extends(self):
        self.assertListEqual(
            list(groupbymax('a' * 100, 200)),
            [['a'] * 100],
        )


class test_Q(Case):

    def test_missing_op(self):
        with self.assertRaises(ValueError):
            Q(foo=30)(Mock())

    def test_missing_op__nested(self):
        with self.assertRaises(ValueError):
            Q(foo__bar__baz=30)(Mock())

    def test_missing_attr(self):
        with self.assertRaises(AttributeError):
            Q(foo__eq=30)(object())

    def test_eq(self):
        self.assertTrue(Q(foo__eq=30)(Mock(foo=30)))

        self.assertFalse(Q(foo__eq=30)(Mock(foo=10)))
        self.assertFalse(Q(foo__eq=30)(Mock(foo=None)))

    def test_eq__True(self):
        self.assertTrue(Q(foo__eq=True)(Mock(foo=True)))
        self.assertTrue(Q(foo__eq=True)(Mock(foo=30)))
        self.assertTrue(Q(foo__eq=True)(Mock(foo='foo')))

        self.assertFalse(Q(foo__eq=True)(Mock(foo='')))
        self.assertFalse(Q(foo__eq=True)(Mock(foo=None)))
        self.assertFalse(Q(foo__eq=True)(Mock(foo=0)))

    def test_eq__False(self):
        self.assertFalse(Q(foo__eq=False)(Mock(foo=True)))
        self.assertFalse(Q(foo__eq=False)(Mock(foo=30)))
        self.assertFalse(Q(foo__eq=False)(Mock(foo='foo')))

        self.assertTrue(Q(foo__eq=False)(Mock(foo='')))
        self.assertTrue(Q(foo__eq=False)(Mock(foo=None)))
        self.assertTrue(Q(foo__eq=False)(Mock(foo=0)))

    def test_ne(self):
        self.assertTrue(Q(foo__ne=30)(Mock(foo=20)))
        self.assertTrue(Q(foo__ne=30)(Mock(foo=None)))

        self.assertFalse(Q(foo__ne=30)(Mock(foo=30)))

    def test_gt(self):
        self.assertTrue(Q(foo__gt=30)(Mock(foo=31)))

        self.assertFalse(Q(foo__gt=30)(Mock(foo=30)))

    def test_gte(self):
        self.assertTrue(Q(foo__gte=30)(Mock(foo=31)))
        self.assertTrue(Q(foo__gte=30)(Mock(foo=30)))

        self.assertFalse(Q(foo__gte=30)(Mock(foo=29)))

    def test_lt(self):
        self.assertTrue(Q(foo__lt=30)(Mock(foo=29)))

        self.assertFalse(Q(foo__lt=30)(Mock(foo=30)))

    def test_lte(self):
        self.assertTrue(Q(foo__lte=30)(Mock(foo=29)))
        self.assertTrue(Q(foo__lte=30)(Mock(foo=30)))

        self.assertFalse(Q(foo__lte=30)(Mock(foo=31)))

    def test_contains(self):
        self.assertTrue(
            Q(foo__contains='_')(Mock(foo='the_quick')),
        )
        self.assertFalse(
            Q(foo__contains='_')(Mock(foo='the!quick')),
        )

    def test_startswith(self):
        self.assertTrue(
            Q(foo__startswith='_')(Mock(foo='_the_quick')),
        )
        self.assertFalse(
            Q(foo__startswith='_')(Mock(foo='!the!quick')),
        )

    def test_endswith(self):
        self.assertTrue(
            Q(foo__endswith='_')(Mock(foo='the_quick_')),
        )
        self.assertFalse(
            Q(foo__endswith='_')(Mock(foo='the!quick!')),
        )

    def test_is(self):
        obj = object()
        self.assertTrue(Q(foo__is=None)(Mock(foo=None)))
        self.assertTrue(Q(foo__is=obj)(Mock(foo=obj)))
        self.assertFalse(Q(foo__is=None)(Mock(foo=0)))
        self.assertFalse(Q(foo__is=obj)(Mock(foo=object())))

    def test_is_not(self):
        obj = object()
        self.assertTrue(Q(foo__is_not=None)(Mock(foo=0)))
        self.assertTrue(Q(foo__is_not=obj)(Mock(foo=object())))
        self.assertFalse(Q(foo__is_not=None)(Mock(foo=None)))
        self.assertFalse(Q(foo__is_not=obj)(Mock(foo=obj)))

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
        self.assertTrue(
            Q(author__is_staff__eq=True,
              author__full_name__contains=' ',
              author__full_name__startswith='George',
              author__full_name__endswith='Costanza',
              author__rank__gt=2.3,
              author__violations__is=None,
              tags__contains='abc')(obj)
        )
        self.assertFalse(
            Q(author__is_staff__eq=True,
              author__full_name__contains=' ',
              author__full_name__startswith='George',
              author__full_name__endswith='Costanza',
              author__rank__gt=2.3,
              author__violations__is=None,
              tags__contains='zzz')(obj)
        )
        self.assertFalse(
            Q(author__is_staff__eq=False,
              author__full_name__contains=' ',
              author__full_name__startswith='George',
              author__full_name__endswith='Costanza',
              author__rank__gt=2.3,
              author__violations__is=None)(obj)
        )

    def test_all_must_match(self):
        obj = Mock(
            full_name='George Costanza',
            is_staff=True,
            rank=3.03,
            violations=None,
        )
        self.assertTrue(
            Q(is_staff__eq=True,
              full_name__contains=' ',
              full_name__startswith='George',
              full_name__endswith='Costanza',
              rank__gt=2.3,
              violations__is=None)(obj)
        )
        self.assertFalse(
            Q(is_staff__eq=False,
              full_name__contains=' ',
              full_name__startswith='George',
              full_name__endswith='Costanza',
              rank__gt=2.3,
              violations__is=None)(obj)
        )

    def test_nested_Q_objects(self):
        x = Mock(foo=Mock(bar=1, baz=2))
        q1 = Q(Q(foo__x__eq=True), foo__bar__eq=1) & Q(foo__baz__eq=2)
        q2 = Q(foo__bar__eq=1) & Q(foo__baz__eq=3)
        q3 = Q(foo__baz__eq=3) | Q(foo__bar__eq=1)
        q4 = Q(foo__bar__eq=1) & Q(Q(foo__x__ne=True), foo__baz__eq=2)
        self.assertTrue(q1(x))
        self.assertFalse(q2(x))
        self.assertTrue((~q2)(x))

        self.assertTrue(q3(x))
        self.assertFalse(q4(x))

    def test_now_eq(self):
        x1 = Mock(foo=Mock(bar=1, baz=2))
        x1._previous_version = Mock(foo=Mock(bar=0, baz=2))
        q = Q(foo__bar__now_eq=1)
        self.assertTrue(q(x1))

        x2 = Mock(foo=Mock(bar=1, baz=2))
        x2._previous_version = Mock(foo=Mock(bar=1, baz=2))
        self.assertFalse(q(x2))

        x3 = Mock(state1='PUBLISHED', state2='PUBLISHED')
        x3._previous_version = Mock(
            state1='PENDING', state2='PUBLISHED',
        )
        self.assertTrue(Q(state1__now_eq='PUBLISHED')(x3))
        self.assertFalse(Q(state2__now_eq='PUBLISHED')(x3))

    def test_now_ne(self):
        x1 = Mock(foo=Mock(bar=1, baz=1))
        x1._previous_version = Mock(foo=Mock(bar=0, baz=2))
        self.assertTrue(Q(foo__bar__now_ne=2)(x1))
        self.assertFalse(Q(foo__baz__now_ne=2)(x1))

    def test_now_gt(self):
        x1 = Mock(foo=Mock(bar=22, baz=22))
        x1._previous_version = Mock(foo=Mock(bar=10, baz=42))
        self.assertTrue(Q(foo__bar__now_gt=20)(x1))
        self.assertFalse(Q(foo__baz__now_gt=20)(x1))

    def test_now_lt(self):
        x1 = Mock(foo=Mock(bar=22, baz=22))
        x1._previous_version = Mock(foo=Mock(bar=42, baz=12))
        self.assertTrue(Q(foo__bar__now_lt=40)(x1))
        self.assertFalse(Q(foo__baz__now_lt=40)(x1))

    def test_now_gte(self):
        x1 = Mock(foo=Mock(bar=22, baz=22))
        x1._previous_version = Mock(foo=Mock(bar=22, baz=42))
        self.assertTrue(Q(foo__bar__now_gte=22)(x1))
        self.assertFalse(Q(foo__baz__now_gte=22)(x1))

    def test_now_lte(self):
        x1 = Mock(foo=Mock(bar=22, baz=22))
        x1._previous_version = Mock(foo=Mock(bar=42, baz=12))
        self.assertTrue(Q(foo__bar__now_lte=22)(x1))
        self.assertFalse(Q(foo__baz__now_lte=22)(x1))

    def test_now_is(self):
        x1 = Mock(foo=Mock(bar=None, baz=None))
        x1._previous_version = Mock(foo=Mock(bar=30, baz=None))
        self.assertTrue(Q(foo__bar__now_is=None)(x1))
        self.assertFalse(Q(foo__baz__now_is=None)(x1))

    def test_now_is_not(self):
        x1 = Mock(foo=Mock(bar=30, baz=30))
        x1._previous_version = Mock(foo=Mock(bar=None, baz=10))
        self.assertTrue(Q(foo__bar__now_is_not=None)(x1))
        self.assertFalse(Q(foo__baz__now_is_not=None)(x1))

    def test_now_contains(self):
        x1 = Mock(foo=Mock(
            bar='The quick brown fox',
            baz='The quick brown fox'),
        )
        x1._previous_version = Mock(foo=Mock(
            bar='The quick red fox',
            baz='The quick brown fox',
        ))
        self.assertTrue(Q(foo__bar__now_contains='brown')(x1))
        self.assertFalse(Q(foo__baz__now_contains='brown')(x1))

    def test_now_startswith(self):
        x1 = Mock(foo=Mock(
            bar='The quick brown fox',
            baz='The quick brown fox',
        ))
        x1._previous_version = Mock(foo=Mock(
            bar='The lazy brown fox',
            baz='The quick brown fox',
        ))
        self.assertTrue(Q(foo__bar__now_startswith='The quick')(x1))
        self.assertFalse(Q(foo__baz__now_startswith='The quick')(x1))

    def test_now_endswith(self):
        x1 = Mock(foo=Mock(
            bar='The quick brown fox',
            baz='The quick brown fox',
        ))
        x1._previous_version = Mock(foo=Mock(
            bar='The lazy red fox',
            baz='The lazy brown fox',
        ))
        self.assertTrue(Q(foo__bar__now_endswith='brown fox')(x1))
        self.assertFalse(Q(foo__baz__now_endswith='brown fox')(x1))

    def test_in(self):
        x1 = Mock(foo=Mock(
            bar='PUBLISHED',
            baz='PENDING',
        ))
        self.assertTrue(Q(foo__bar__in={'PUBLISHED', 'X', 'Y', 'Z'})(x1))
        self.assertFalse(Q(foo__baz__in={'PUBLISHED', 'X', 'Y', 'Z'})(x1))

    def test_now_in(self):
        x1 = Mock(foo=Mock(
            bar='PUBLISHED',
            baz='PUBLISHED',
        ))
        x1._previous_version = Mock(foo=Mock(
            bar='PENDING',
            baz='PUBLISHED',
        ))
        self.assertTrue(Q(foo__bar__now_in={'PUBLISHED', 'X', 'Y', 'Z'})(x1))
        self.assertFalse(Q(foo__baz__now_in={'PUBLISHED', 'X', 'Y', 'Z'})(x1))

    def test_not_in(self):
        x1 = Mock(foo=Mock(
            bar='PUBLISHED',
            baz='PENDING',
        ))
        self.assertTrue(Q(foo__bar__not_in={'PENDING', 'X', 'Y', 'Z'})(x1))
        self.assertFalse(Q(foo__baz__not_in={'PENDING', 'X', 'Y', 'Z'})(x1))

    def test_now_not_in(self):
        x1 = Mock(foo=Mock(
            bar='PUBLISHED',
            baz='PUBLISHED',
        ))
        x1._previous_version = Mock(foo=Mock(
            bar='PENDING',
            baz='PUBLISHED',
        ))
        self.assertTrue(
            Q(foo__bar__now_not_in={'PENDING', 'X', 'Y', 'Z'})(x1),
        )
        self.assertFalse(
            Q(foo__baz__now_not_in={'PENDING', 'X', 'Y', 'Z'})(x1),
        )
