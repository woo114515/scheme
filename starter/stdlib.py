"""任务 5：内置过程（标准函数库）。

build_env() 返回一个填满内置过程的 Env。内置过程就是普通 Python
函数（或 lambda），按 spec.md 第 4 节的语义实现，可变参数用 *args 接收。

要点：
- 算术：+ - * 可变参数；- 单参数时取反；/ 全部是整数时得整数商；
  单参数 / 求倒数。modulo/quotient 对整数运算。expt 乘方，abs 绝对值。
- 比较：= < > <= >= 链式比较（相邻两两比较都成立才为 #t），
  支持数字和符号。
- not：只有 #f 才是假——Python 里 0、空列表都为假，不能用 Python 的
  not，要写 (x is False)。
- 列表值在运行时是"点对链"：(1 2 3) 是 (1, (2, (3, ())))。
  cons 产生 (a, b)；car 取 [0]；cdr 取 [1]；空表是 ()。
  null? 判断是否为 ()；pair? 判断是否为非空 tuple；list? 沿 cdr 链
  走到头必须是 ()。
- equal? 递归比较结构；eq? 对数字/符号/布尔按值比较，对 tuple 按
  身份（is）比较。
- display 用 to_str(x, quotes=False) 打印、不换行、返回 None；
  newline 打印换行、返回 None。
- 出错时抛 TypeError，消息里带上 to_str 打印的值。

依赖：environment.Env、environment.Procedure、parser.Symbol、printer.to_str。
"""

from environment import Env, Procedure
from parser import Symbol
from printer import to_str

# TODO: 让 AI 实现 build_env 和它需要的辅助函数
# （数值检查、结构相等、is_list、链式比较构造器等）。


def build_env():
    raise NotImplementedError("TODO: 实现 build_env")
