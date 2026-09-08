"""The initial global environment: built-in procedures.

Helpers: is_num, nums, scheme_equal, is_list, cmp_key, make_cmp.
"""

import functools
import sys

from environment import Env, Procedure
from parser import Symbol
from printer import to_str


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def nums(*args):
    for a in args:
        if not is_num(a):
            raise TypeError(f"expected a number, got {to_str(a)}")
    return args


def scheme_equal(a, b):
    if isinstance(a, tuple) or isinstance(b, tuple):
        if not (isinstance(a, tuple) and isinstance(b, tuple)):
            return False
        if a == () or b == ():
            return a == b
        return scheme_equal(a[0], b[0]) and scheme_equal(a[1], b[1])
    if type(a) is not type(b):
        return False
    return a == b


def is_list(x):
    while isinstance(x, tuple) and x != ():
        x = x[1]
    return x == ()


def cmp_key(x):
    if is_num(x) or isinstance(x, Symbol):
        return x
    raise TypeError(f"cannot compare {to_str(x)}")


def make_cmp(op):
    def f(*args):
        keys = [cmp_key(a) for a in args]
        for x, y in zip(keys, keys[1:]):
            if not op(x, y):
                return False
        return True
    return f


def build_env():
    env = Env()

    def sub(*a):
        nums(*a)
        if len(a) == 1:
            return -a[0]
        return functools.reduce(lambda x, y: x - y, a)

    def div(*a):
        nums(*a)
        if len(a) == 1:
            return 1 / a[0]
        ints = all(isinstance(x, int) for x in a)
        result = functools.reduce(lambda x, y: x / y, a)
        return int(result) if ints else result

    def modulo(a, b):
        nums(a, b)
        return int(a) % int(b)

    def quotient(a, b):
        nums(a, b)
        return int(a / b)

    def expt(a, b):
        nums(a, b)
        result = a ** b
        return int(result) if isinstance(a, int) and isinstance(b, int) and b >= 0 else result

    def car(p):
        if not isinstance(p, tuple) or p == ():
            raise TypeError(f"car: expected a pair, got {to_str(p)}")
        return p[0]

    def cdr(p):
        if not isinstance(p, tuple) or p == ():
            raise TypeError(f"cdr: expected a pair, got {to_str(p)}")
        return p[1]

    def mklist(*items):
        result = ()
        for item in reversed(items):
            result = (item, result)
        return result

    def length(lst):
        n = 0
        while isinstance(lst, tuple) and lst != ():
            n += 1
            lst = lst[1]
        if lst != ():
            raise TypeError(f"length: expected a list, got {to_str(lst)}")
        return n

    def append2(x, y):
        if x == ():
            return y
        return (x[0], append2(x[1], y))

    def append(*lists):
        result = ()
        for lst in lists:
            result = append2(result, lst)
        return result

    def eq(a, b):
        if (isinstance(a, tuple) or isinstance(b, tuple)
                or isinstance(a, Procedure) or isinstance(b, Procedure)
                or callable(a) or callable(b)):
            return a is b
        if type(a) is not type(b):
            return False
        return a == b

    def display(x):
        sys.stdout.write(to_str(x, quotes=False))
        return None

    def newline():
        print()
        return None

    env.update({
        # arithmetic
        "+": lambda *a: sum(nums(*a)),
        "-": sub,
        "*": lambda *a: functools.reduce(lambda x, y: x * y, nums(*a), 1),
        "/": div,
        "modulo": modulo,
        "quotient": quotient,
        "expt": expt,
        "abs": lambda x: abs(nums(x)[0]),
        # comparisons
        "=": make_cmp(lambda x, y: x == y),
        "<": make_cmp(lambda x, y: x < y),
        ">": make_cmp(lambda x, y: x > y),
        "<=": make_cmp(lambda x, y: x <= y),
        ">=": make_cmp(lambda x, y: x >= y),
        "equal?": scheme_equal,
        "eq?": eq,
        # boolean
        "not": lambda x: x is False,
        # pairs and lists
        "cons": lambda a, b: (a, b),
        "car": car,
        "cdr": cdr,
        "list": mklist,
        "length": length,
        "append": append,
        "null?": lambda x: isinstance(x, tuple) and x == (),
        "pair?": lambda x: isinstance(x, tuple) and x != (),
        "list?": is_list,
        # predicates
        "number?": is_num,
        "boolean?": lambda x: isinstance(x, bool),
        "symbol?": lambda x: isinstance(x, Symbol),
        "string?": lambda x: isinstance(x, str) and not isinstance(x, Symbol),
        "procedure?": lambda x: isinstance(x, Procedure) or callable(x),
        "zero?": lambda x: nums(x) and x == 0,
        "even?": lambda x: nums(x) and x % 2 == 0,
        "odd?": lambda x: nums(x) and x % 2 != 0,
        # output
        "display": display,
        "newline": newline,
    })
    return env
