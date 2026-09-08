"""mini-Scheme reference interpreter.

A Scheme subset modeled on the core of CS61A's Scheme (and Norvig's
lis.py). Reads one or more .scm files (or standard input when no file
is given), evaluates each top-level expression in order in a single
global environment, and prints each result on its own line.

Usage:
    python3 minischeme.py file.scm [more.scm ...]
"""

import functools
import sys


class Symbol(str):
    """A Scheme symbol. Subclasses str so it can serve as an env key."""


class Procedure:
    """A user-defined closure: lambda params, body expressions, defining env."""

    def __init__(self, parms, body, env):
        self.parms = parms
        self.body = body
        self.env = env


class Env(dict):
    """A lexical scope: symbol bindings plus an outer scope."""

    def __init__(self, parms=(), args=(), outer=None):
        super().__init__(zip(parms, args))
        self.outer = outer

    def find(self, var):
        if var in self:
            return self
        if self.outer is not None:
            return self.outer.find(var)
        raise NameError(f"unbound symbol: {var}")


_SYMBOLS = {}


def sym(name):
    """Intern symbols so eq? on identical names holds by identity."""
    return _SYMBOLS.setdefault(name, Symbol(name))


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def tokenize(program):
    tokens = []
    i = 0
    n = len(program)
    while i < n:
        c = program[i]
        if c in "()":
            tokens.append(c)
            i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            j = i + 1
            while j < n and program[j] != '"':
                if program[j] == "\\":
                    j += 1
                j += 1
            tokens.append(program[i:j + 1])
            i = j + 1
        else:
            j = i
            while j < n and not program[j].isspace() and program[j] not in '()"':
                j += 1
            tokens.append(program[i:j])
            i = j
    return tokens


_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


def parse_string(body):
    out = []
    i = 0
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body) and body[i + 1] in _ESCAPES:
            out.append(_ESCAPES[body[i + 1]])
            i += 2
        else:
            out.append(body[i])
            i += 1
    return "".join(out)


def atom(token):
    if token == "#t":
        return True
    if token == "#f":
        return False
    if token.startswith('"'):
        return parse_string(token[1:-1])
    if token.startswith("'"):
        return ("quote", atom(token[1:]))
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        return sym(token)


def read_from_tokens(tokens):
    if not tokens:
        raise SyntaxError("unexpected end of input")
    token = tokens.pop(0)
    if token == "'":
        return ("quote", read_from_tokens(tokens))
    if token == "(":
        items = []
        while tokens and tokens[0] != ")":
            items.append(read_from_tokens(tokens))
        if not tokens:
            raise SyntaxError("unexpected end of input")
        tokens.pop(0)
        return tuple(items)
    if token == ")":
        raise SyntaxError("unexpected )")
    return atom(token)


def parse(program):
    program = "\n".join(line.split(";", 1)[0] for line in program.splitlines())
    tokens = tokenize(program)
    exprs = []
    while tokens:
        exprs.append(read_from_tokens(tokens))
    return exprs


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------

def to_str(x, quotes=True):
    if x is True:
        return "#t"
    if x is False:
        return "#f"
    if x is None:
        return ""
    if isinstance(x, Symbol):
        return str(x)
    if isinstance(x, str):
        return f'"{x}"' if quotes else x
    if isinstance(x, (int, float)):
        return str(x)
    if isinstance(x, tuple):
        parts = []
        cur = x
        while isinstance(cur, tuple) and cur != ():
            parts.append(to_str(cur[0], quotes))
            cur = cur[1]
        if cur == ():
            return "(" + " ".join(parts) + ")"
        return "(" + " ".join(parts) + " . " + to_str(cur, quotes) + ")"
    if isinstance(x, Procedure) or callable(x):
        return "#<procedure>"
    return str(x)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

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


def to_chain(data):
    """Convert a flat tuple (as the reader produces for quoted data) into
    a proper cons chain, so quoted lists behave like cons results."""
    if not isinstance(data, tuple):
        return data
    result = ()
    for item in reversed(data):
        result = (to_chain(item), result)
    return result


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


def eval_(expr, env):
    if isinstance(expr, Symbol):
        return env.find(expr)[expr]
    if not isinstance(expr, tuple):
        return expr  # literal: number, boolean, string
    op, *args = expr

    if op == "quote":
        return to_chain(args[0])
    if op == "if":
        test, conseq = args[0], args[1]
        alt = args[2] if len(args) > 2 else None
        return eval_(conseq if eval_(test, env) is not False else alt, env)
    if op == "cond":
        for clause in args:
            test, *body = clause
            value = True if test == "else" else eval_(test, env)
            if value is not False:
                return eval_(("begin",) + tuple(body), env) if body else value
        return None
    if op == "and":
        result = True
        for e in args:
            result = eval_(e, env)
            if result is False:
                return False
        return result
    if op == "or":
        result = False
        for e in args:
            result = eval_(e, env)
            if result is not False:
                return result
        return result
    if op == "define":
        target, *body = args
        if isinstance(target, tuple):
            name = target[0]
            env[name] = eval_(("lambda", target[1:]) + tuple(body), env)
        else:
            name = target
            env[name] = eval_(body[0], env)
        return name
    if op == "lambda":
        parms, *body = args
        return Procedure(parms, body, env)
    if op == "let":
        bindings, *body = args
        names = tuple(n for n, _ in bindings)
        values = tuple(eval_(e, env) for _, e in bindings)
        return eval_(("begin",) + tuple(body), Env(names, values, env))
    if op == "begin":
        result = None
        for e in args:
            result = eval_(e, env)
        return result

    proc = eval_(op, env)
    values = [eval_(a, env) for a in args]
    return apply_(proc, values)


def apply_(proc, args):
    if isinstance(proc, Procedure):
        if len(args) != len(proc.parms):
            raise TypeError(f"expected {len(proc.parms)} arguments, got {len(args)}")
        return eval_(("begin",) + tuple(proc.body), Env(proc.parms, args, proc.env))
    if callable(proc):
        return proc(*args)
    raise TypeError(f"not a procedure: {to_str(proc)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(program, env):
    for expr in parse(program):
        result = eval_(expr, env)
        if result is not None:
            print(to_str(result))


def main():
    sys.setrecursionlimit(20000)
    env = build_env()
    files = sys.argv[1:]
    try:
        if files:
            for path in files:
                with open(path, encoding="utf-8") as fh:
                    run(fh.read(), env)
        else:
            run(sys.stdin.read(), env)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
