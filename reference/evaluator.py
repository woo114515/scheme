"""The heart of the interpreter: evaluate and apply.

evaluate(expr, env) evaluates an expression in an environment.
apply(proc, args) calls a built-in or user-defined procedure.
"""

from environment import Env, Procedure
from parser import Symbol, to_chain
from printer import to_str


def evaluate(expr, env):
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
        return evaluate(conseq if evaluate(test, env) is not False else alt, env)
    if op == "cond":
        for clause in args:
            test, *body = clause
            value = True if test == "else" else evaluate(test, env)
            if value is not False:
                return evaluate(("begin",) + tuple(body), env) if body else value
        return None
    if op == "and":
        result = True
        for e in args:
            result = evaluate(e, env)
            if result is False:
                return False
        return result
    if op == "or":
        result = False
        for e in args:
            result = evaluate(e, env)
            if result is not False:
                return result
        return result
    if op == "define":
        target, *body = args
        if isinstance(target, tuple):
            name = target[0]
            env[name] = evaluate(("lambda", target[1:]) + tuple(body), env)
        else:
            name = target
            env[name] = evaluate(body[0], env)
        return name
    if op == "lambda":
        parms, *body = args
        return Procedure(parms, body, env)
    if op == "let":
        bindings, *body = args
        names = tuple(n for n, _ in bindings)
        values = tuple(evaluate(e, env) for _, e in bindings)
        return evaluate(("begin",) + tuple(body), Env(names, values, env))
    if op == "begin":
        result = None
        for e in args:
            result = evaluate(e, env)
        return result

    proc = evaluate(op, env)
    values = [evaluate(a, env) for a in args]
    return apply(proc, values)


def apply(proc, args):
    if isinstance(proc, Procedure):
        if len(args) != len(proc.parms):
            raise TypeError(f"expected {len(proc.parms)} arguments, got {len(args)}")
        return evaluate(("begin",) + tuple(proc.body), Env(proc.parms, args, proc.env))
    if callable(proc):
        return proc(*args)
    raise TypeError(f"not a procedure: {to_str(proc)}")
