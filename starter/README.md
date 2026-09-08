# mini-Scheme 起步骨架

你的任务：**和 AI 结对（vibe coding）**，把本目录补成一个符合 `../spec.md` 的 mini-Scheme 解释器。你不需要会编程——你负责向 AI 描述需求、验证结果、报错时继续迭代。

## 模块地图（数据如何流动）

```
程序文本 (.scm)
   │ tokenizer.tokenize        → 词列表 ['(', '+', '1', '2', ')']
   ↓
parser.parse                    → 表达式（嵌套的 Python 数据）
   ↓
evaluator.evaluate              → 值（查 environment.Env、调 stdlib 内置过程、parser.to_chain 处理引用）
   ↓
printer.to_str                  → 打印成规范第 5 节的写法
```

每个模块的职责和接口都写在该文件的 docstring 里。**把整个文件的 docstring 复制给 AI，让它实现，然后跑测试验证。**

## 建议完成顺序（自底向上）

1. `tokenizer.py` — 最简单，先拿下
2. `parser.py` — 文本变成数据结构
3. `printer.py` — 值变成文本（和 1、2 正好相反）
4. `environment.py` — 变量作用域
5. `stdlib.py` — 内置函数库
6. `evaluator.py` — 求值器，把上面全部串起来

`main.py` 已写好，不用改。

## 测试

在仓库根目录运行：

```
python3 tests/run_tests.py python3 starter/main.py
```

- 用例按难度从 001 到 012 排列。**别一次冲全部**：先让 001 通过，再逐步推进。
- 测试通过 ≠ 结束：看看 `tests/cases/*.scm` 里的程序，确认你能讲清楚它为什么是这个输出。

## 评分关注

- **模块化**：每个文件只做一件事，接口按 docstring 约定；不把所有代码堆进一个文件。
- **能否独立验证**：AI 每改完一个模块，就运行测试确认，而不是全部写完再测。
- **迭代能力**：报错时能否描述现象、看懂输出差异并让 AI 修正。
