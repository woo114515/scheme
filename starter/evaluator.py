"""任务 6：求值器——解释器的心脏。

evaluate(expr, env) 求值一个表达式：
- Symbol → 在环境中查它的值：env.find(expr)[expr]。
- 非 tuple → 字面量（数字/布尔/字符串），原样返回。
- tuple → 第一个元素是操作符，分两类：

  特殊形式（按 spec.md 第 3 节，注意求值顺序）：
  - (quote 数据) → parser.to_chain(数据)，不求值
  - (if 测试 真分支 假分支?) → 先求值测试，只求值一个分支；假分支可省略
  - (cond (测试 表达式...) ...) → 从上到下；else 子句兜底；子句无
    表达式时返回测试值；全不匹配返回 None
  - (and e1 e2 ...) / (or e1 e2 ...) → 短路求值；(and) → True，
    (or) → False。注意只有 x is False 才假
  - (define 名 表达式) → 在当前环境绑定，返回符号名本身；
    (define (名 参数...) 体...) 是 define + lambda 的简写
  - (lambda (参数...) 体...) → 返回 environment.Procedure，
    捕获当前环境（闭包）
  - (let ((名 表达式)...) 体...) → 各表达式**先在外部环境求值**，
    再建新环境并行绑定，求值函数体
  - (begin e1 e2 ...) → 从左到右，返回最后一个

  函数调用：先求值操作符和每个实参，再 apply(proc, args)。

apply(proc, args) 调用一个过程：
- Procedure → 检查参数个数，创建新环境（外层是定义时的环境），
  按 begin 语义求值函数体。
- 普通 Python callable（内置过程）→ 直接调用。
- 其他 → 抛 TypeError。

依赖：environment.Env、environment.Procedure、parser.Symbol、
parser.to_chain。错误消息可用 printer.to_str 打印值。
"""

from environment import Env, Procedure
from parser import Symbol, to_chain

# TODO: 让 AI 实现 evaluate 和 apply。


def evaluate(expr, env):
    raise NotImplementedError("TODO: 实现 evaluate")


def apply(proc, args):
    raise NotImplementedError("TODO: 实现 apply")
