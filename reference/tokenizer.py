"""Tokenize mini-Scheme source text into tokens.

A token is one of: "(", ")", a string literal (with its quotes), or a
bare atom such as 42, #t, foo, or the quote shorthand 'x.

>>> tokenize("(+ 1 2)")
['(', '+', '1', '2', ')']
"""


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
