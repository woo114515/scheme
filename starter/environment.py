"""任务 4：作用域（环境）与闭包（过程）。

环境（Env）：记录"名字 → 值"的对应关系，并能向外层查找。
- 全局环境在最外层，stdlib 会用它。
- 每次调用用户定义的函数时，创建一个新环境，把实参绑定到参数名，
  外层指向函数**定义时**所在的环境——这就是"词法作用域"。
- find(var) 返回"绑定了 var 的那个环境"（而不是值本身），
  调用方用 [var] 取值；找不到就抛 NameError。

过程（Procedure）：用户用 lambda/define 定义的函数，由三样东西组成：
参数名 tuple、函数体表达式 tuple、定义时的环境（闭包）。

依赖：无。
"""


class Env(dict):
    """名字 → 值 的映射 + 外层环境指针。

    __init__(self, parms=(), args=(), outer=None)：
      用 zip(parms, args) 建立参数绑定，并记录 outer。
    find(self, var)：
      自身有 var 就返回 self；否则向外层递归查找；
      都没有就 raise NameError。
    """
    def __init__(self, parms=(), args=(), outer=None):
        raise NotImplementedError("TODO: 实现 Env.__init__")

    def find(self, var):
        raise NotImplementedError("TODO: 实现 Env.find")


class Procedure:
    """用户定义的过程：参数名 tuple、函数体 tuple、定义时的环境。

    调用它的逻辑在 evaluator.apply 里，这里只保存这三样东西。
    """
    def __init__(self, parms, body, env):
        self.parms = parms
        self.body = body
        self.env = env
