"""Parse tokens into Scheme expressions.

Expressions are Python values: ints, floats, booleans, strings,
interned Symbol objects, and flat tuples such as ('+', 1, 2) for
compound expressions. Quoted data is converted to cons chains by
to_chain when (quote ...) is evaluated (see evaluator.py).
"""

from tokenizer import tokenize


class Symbol(str):
    """A Scheme symbol. Subclasses str so it can serve as an env key."""


_SYMBOLS = {}


def sym(name):
    """Intern symbols so eq? on identical names holds by identity."""
    return _SYMBOLS.setdefault(name, Symbol(name))


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
    """Strip comments, tokenize, and read every top-level expression."""
    program = "\n".join(line.split(";", 1)[0] for line in program.splitlines())
    tokens = tokenize(program)
    exprs = []
    while tokens:
        exprs.append(read_from_tokens(tokens))
    return exprs


def to_chain(data):
    """Convert a flat tuple (as the reader produces for quoted data) into
    a proper cons chain, so quoted lists behave like cons results."""
    if not isinstance(data, tuple):
        return data
    result = ()
    for item in reversed(data):
        result = (to_chain(item), result)
    return result
