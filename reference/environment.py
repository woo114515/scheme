"""Environments (lexical scopes) and user-defined procedures (closures)."""


class Env(dict):
    """A lexical scope: symbol bindings plus an outer scope."""

    def __init__(self, parms=(), args=(), outer=None):
        super().__init__(zip(parms, args))
        self.outer = outer

    def find(self, var):
        """Return the innermost Env that binds var, or raise NameError."""
        if var in self:
            return self
        if self.outer is not None:
            return self.outer.find(var)
        raise NameError(f"unbound symbol: {var}")


class Procedure:
    """A user-defined closure: lambda params, body expressions, defining env."""

    def __init__(self, parms, body, env):
        self.parms = parms
        self.body = body
        self.env = env
