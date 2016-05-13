"""

    thorn.utils.functional
    ======================

    Functional-style utilities.

"""
from __future__ import absolute_import, unicode_literals

import operator

from functools import partial

from celery.utils import cached_property

try:
    from django.db.models.query import Q as _Q_
except ImportError:  # pragma: no cover
    from .django.query_utils import Q as _Q_  # noqa

__all__ = ['groupbymax', 'Q']

E_FILTER_FIELD_MISSING_OP = """\
filter field argument {0!r} not allowed: did you mean '{0}__eq'?\
"""


def not_contains(a, b):
    """``not_contains(a, b) -> b not in a``"""
    return b not in a


def startswith(a, b):
    """``startswith(a, b) -> a.startswith(b)``"""
    return a.startswith(b)


def endswith(a, b):
    """``endswith(a, b) -> a.endswith(b)``"""
    return a.endswith(b)


def reverse_n(N, tup):
    """Reverse n first elements in a tuple."""
    return tuple(reversed(tup[:N])) + tup[N:] if N else tuple(reversed(tup))


def negate(fun):
    """Return function negating the value of a boolean function."""

    def negated(*args, **kwargs):
        return not fun(*args, **kwargs)
    return negated


def reverse_arguments(N):
    """Returns transformed function where the first N arguments are
    reversed."""

    def _inner(fun):
        def reversed(*args, **kwargs):
            return fun(*reverse_n(N, args), **kwargs)
        return reversed
    return _inner


def wrap_transition(op, did_change):
    """Transforms operator into a transition operator, i.e. one that
    only returns true if the ``did_change`` operator also returns true.

    E.g. ``wrap_transition(operator.eq, operator.ne)`` returns function
    with signature ``(new_value, needle, old_value)`` and only returns
    true if new_value is equal to needle, but old_value was not equal
    to needle.

    """

    def compare(new_value, needle, old_value):
        return did_change(old_value, needle) and op(new_value, needle)

    return compare


def groupbymax(it, max, key=operator.eq, sentinel=object()):
    """Given an iterator emitting items in sorted order, this will
    group items together based on the key function, and produces
    one list for each group.

    :param it: Iterator emitting item in order.
    :param max: Maximum size of any group (mandatory).
    :keyword key: Function used to compare items.
        Defaults to :func:`operator.eq` matching values exactly.

    Examples:

    .. code-block:: pycon

        >>> x = ['A', 'A', 'A', 'B', 'C', 'D', 'D', 'E']
        >>> list(groupbymax(x, 3))
        [['A', 'A', 'A'], ['A'], ['B'], ['C'], ['D', 'D'], ['E']]

        # NOTE: Not technically sorted, but similar items appear in the
        # order we're matching for.
        >>> x = [('foo:A', 'foo:B', 'bar:C', 'baz:D', 'baz:E', 'baz:F']
        >>> list(groupbymax(x, 10,
        ...     key=lambda a, b: a.split(':')[0] == b.split(':')[0]))
        [['foo:A', 'foo:B'], ['bar:C'], ['baz:D', 'baz:E', 'baz:F']]

    """
    it = iter(it)
    for item in it:
        buf = []
        while 1:
            nxt = next(it, sentinel)
            if nxt is sentinel or (
                    not key(nxt, item) or len(buf) >= max - 1):
                yield [item] + buf if buf else [item]
                if nxt is not sentinel:
                    yield [nxt]
                break
            buf.append(nxt)


class Q(_Q_):
    """Object query node.

    This class works like :class:`django.db.models.Q`, but is used for
    filtering regular Python objects instead of database rows.

    **Examples**

    - Match object with ``last_name`` attribute set to "Costanza"::

        Q(last_name__eq="Costanza")

    - Match object with ``author.last_name`` attribute set to "Benes"::

        Q(author__last_name__eq="Benes")

    - You are not allowed to specify any key without an operator,
      event though the following would be fine using Django`s Q objects::

        Q(author__last_name="Benes")   # <-- ERROR, will raise ValueError

    - Attributes can be nested arbitrarily deep::

        Q(a__b__c__d__e__f__g__x__gt=3.03)

    - The special ``*__eq=True`` means "match any *true-ish* value"::

        Q(author__account__is_staff__eq=True)

    - Similarly the ``*__eq=False`` means "match any *false-y*" value"::

        Q(author__account__is_disabled=False)

    See :ref:`events-model-filtering-operators`.

    :returns: :class:`collections.Callable`, to match an object with
      the given predicates, call the return value with the object to match:
      ``Q(x__eq==808)(obj)``.

    """

    #: The gate decides the boolean operator of this tree node.
    #: A node can either be *OR* (``a | b``), or an *AND* note (``a & b``).
    #: - Default is *AND*.
    gates = {
        _Q_.OR: any,
        _Q_.AND: all,
    }

    #: If the node is negated (``~a`` / ``a.negate()``), branch will be True,
    #: and we reverse the query into a ``not a`` one.
    branches = {
        True: operator.not_,
        False: operator.truth,
    }

    #: Mapping of opcode to binary operator function: ``f(a, b)``.
    #: Operators may return any true-ish or false-y value.
    operators = {
        'eq': operator.eq,
        'now_eq': wrap_transition(operator.eq, operator.ne),
        'ne': operator.ne,
        'now_ne': wrap_transition(operator.ne, operator.ne),
        'gt': operator.gt,
        'now_gt': wrap_transition(operator.gt, operator.lt),
        'lt': operator.lt,
        'now_lt': wrap_transition(operator.lt, operator.gt),
        'gte': operator.ge,
        'now_gte': wrap_transition(operator.ge, operator.le),
        'lte': operator.le,
        'now_lte': wrap_transition(operator.le, operator.ge),
        'in': reverse_arguments(2)(operator.contains),
        'now_in': wrap_transition(
            reverse_arguments(2)(operator.contains),
            reverse_arguments(2)(not_contains),
        ),
        'not_in': reverse_arguments(2)(not_contains),
        'now_not_in': wrap_transition(
            reverse_arguments(2)(not_contains),
            reverse_arguments(2)(operator.contains),
        ),
        'is': operator.is_,
        'now_is': wrap_transition(operator.is_, operator.is_not),
        'is_not': operator.is_not,
        'now_is_not': wrap_transition(operator.is_not, lambda a, _: a is None),
        'contains': operator.contains,
        'now_contains': wrap_transition(
            operator.contains, negate(operator.contains),
        ),
        'not': lambda x, _: operator.not_(x),
        'true': lambda x, _: operator.truth(x),
        'startswith': startswith,
        'now_startswith': wrap_transition(startswith, negate(startswith)),
        'endswith': endswith,
        'now_endswith': wrap_transition(endswith, negate(endswith)),
    }

    def __call__(self, obj):
        # NOT?( AND|OR(...) )
        return self.branches[self.negated](
            self.gate(f(obj) for f in self.stack)
        )

    def compile(self, fields):
        # this does not traverse the tree, but compiles the nodes
        # in ``self.children`` only.  The nodes below will be compiled
        # and cached when they are called.
        return [self.compile_node(field) for field in fields]

    def compile_node(self, field):
        """Compiles node into a cached function that performs the match.

        :returns: unary :class:`collections.Callable` taking the object
          to match.

        """
        # can embed other Q objects
        if isinstance(field, type(self)):
            return field

        # convert Django Q objects in-place.
        elif isinstance(field, _Q_):
            field.__class__ = type(self)
            return field

        # or it's a key, value pair.
        lhs, rhs = field
        lhs, opcode = self.prepare_statement(lhs, rhs)

        # this creates the new matching function to be added to the stack.
        return self.compile_op(lhs, rhs, opcode)

    def prepare_statement(self, lhs, rhs):
        lhs, _, opcode = lhs.rpartition('__')
        if not opcode or opcode not in self.operators:
            raise ValueError(E_FILTER_FIELD_MISSING_OP.format(lhs))
        return lhs.replace('__', '.'), self.prepare_opcode(opcode, rhs)

    def prepare_opcode(self, O, rhs):
        # eq=True and friends are special, as they should match any
        # true-ish value (__bool__), not check for equality.
        if (O == 'eq' and rhs is True) or O == 'ne' and rhs is False:
            return 'true'
        elif (O == 'eq' and rhs is False) or O == 'ne' and rhs is True:
            return 'not'
        return O

    def compile_op(self, lhs, rhs, opcode):
        return self._compile_op(
            self.apply_trans_op if 'now' in opcode else self.apply_op,
            lhs, rhs, opcode,
        )

    def _compile_op(self, apply, lhs, rhs, opcode, *args):
        return partial(
            apply,
            operator.attrgetter(lhs), self.operators[opcode], rhs, *args
        )

    def apply_op(self, getter, op, rhs, obj, *args):
        # compiled nodes end up being partial versions of this method,
        # with the getter, op and rhs arguments already set.
        return op(getter(obj), rhs, *args)

    def apply_trans_op(self, getter, op, rhs, obj):
        # transition op  (e.g. now_eq) only matches if the
        # value differs from the previous version.
        return self.apply_op(
            getter, op, rhs, obj, getter(obj._previous_version),
        )

    @property
    def gate(self):
        return self.gates[self.connector]

    @cached_property
    def stack(self):
        # the stack is cached on first call.
        return self.compile(self.children)
