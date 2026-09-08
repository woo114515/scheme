"""任务 3：把值打印成 mini-Scheme 的写法。

to_str(x, quotes=True)，规则见 spec.md 第 5 节：
- True → "#t"；False → "#f"；None → ""
- Symbol → 名字本身；普通字符串 → 带双引号（quotes=False 时不带，
  display 用这个模式）
- 数字 → str(x)
- 点对链 → 括号列表写法，如 (1 2 3)；链的末尾不是 () → 点对写法
  (1 . 2)；() → "()"
- Procedure 或可调用对象 → "#<procedure>"

实现提示：从链头开始走 cdr，沿途收集 car 的打印结果；走到 () 用
空格连接；走不到 () 说明是点对，加 " . " 再打印末尾。

依赖：environment.Procedure、parser.Symbol。
"""

from environment import Procedure
from parser import Symbol

# TODO: 让 AI 实现 to_str，然后跑测试验证。


def to_str(x, quotes=True):
    raise NotImplementedError("TODO: 实现 to_str")
