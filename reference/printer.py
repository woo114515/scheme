"""Print Scheme values in write style (spec.md: values' printed form).

Integers print bare, strings with quotes, lists as (1 2 3), improper
pairs as (1 . 2), the empty list as (), procedures as #<procedure>.
With quotes=False (used by display) strings print without quotes.
"""

from environment import Procedure
from parser import Symbol


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
        if not quotes:
            return x
        escaped = (x.replace("\\", "\\\\").replace('"', '\\"')
                    .replace("\n", "\\n").replace("\t", "\\t"))
        return f'"{escaped}"'
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
