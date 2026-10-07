#!/usr/bin/env python3
"""One-click grading for mini-Scheme submissions (instructor-facing).

Scores all three rubric dimensions automatically (rules in rubric.md):
functional (12 groups x 5), modularity (25, from the three probes) and
code quality (15: comments / naming / robustness probes), and writes a
per-submission report following rubric.md's record template. Cheating red
flags are listed but never auto-zero the score -- a second grader reviews
them and decides. --modularity/--quality override the automatic scores.

The .md reports contain group names, classifications and scores only --
never hidden case contents -- so they are safe to keep around. Raw
details (diffs, stderr, probe output) go to the terminal and to
build/reports/logs/<name>.log, which is working material.

Usage:
    python3 tools/grade.py <submission-dir-or-zip>
    python3 tools/grade.py --batch <dir-with-submissions>
    python3 tools/grade.py --public <submission>       # public set, not scored
    python3 tools/grade.py --case=107 <submission>     # single group check
    python3 tools/grade.py --cmd "python3 path/main.py" <submission>
    python3 tools/grade.py --modularity 20 --quality 12 <submission>  # re-grade
"""

import argparse
import ast
import datetime
import io
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tokenize
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tests"))
import run_tests  # noqa: E402

HIDDEN_DIR = os.path.join(REPO_ROOT, "tests", "cases_hidden")
PUBLIC_DIR = os.path.join(REPO_ROOT, "tests", "cases")
DEFAULT_OUT = os.path.join(REPO_ROOT, "build", "reports")

MIN_MATCH_LEN = 12  # 短于此的用例行不参与红线匹配，避免 (+ 1 2) 这类误报
FLAG_PATTERNS = ("tests/", "cases_hidden", "autograder.pyz", "run_tests")
FRONTEND_RE = re.compile(r"(token|lex|parse|print|read)")
EVAL_RE = re.compile(r"(eval|apply|interp)")
CONCENTRATION_THRESHOLD = 0.60  # rubric 探针②："约 60% 行数集中在单个文件"

# rubric §3 注释锚点："解释为什么"的信号词
WHY_MARKERS = re.compile(
    r"因为|由于|所以|避免|防止|为了|否则|以免|注意|以便|"
    r"\b(?:because|avoid|prevent|otherwise|why|since|so that|so|note that"
    r"|to avoid|in order to)\b",
    re.IGNORECASE)

# rubric §3 鲁棒性锚点：规范内非法程序（工具内置常量，与隐藏用例无关）
ROBUSTNESS_PROBES = (
    ("空表 car", "(car '())"),
    ("除零", "(/ 1 0)"),
    ("参数个数", "(define (probe-arity x) x)\n(probe-arity 1 2)"),
)
ROBUSTNESS_TIMEOUT = 10  # 单个探针的超时（秒）


def fail(message):
    print(f"grade.py: {message}", file=sys.stderr)
    sys.exit(2)


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


# ------------------------------------------------------------------ 提交准备

def safe_extract(zip_path, dest):
    """解压 zip；拒绝绝对路径与 .. 逃逸（zip-slip）。失败抛 ValueError。"""
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            parts = member.replace("\\", "/").split("/")
            if member.startswith("/") or ".." in parts or ":" in parts[0]:
                raise ValueError(f"{zip_path}: 压缩包成员路径不安全：{member}")
        zf.extractall(dest)


def locate_src(root):
    """Return (src_dir, note). 优先 <dir>/src/main.py；退化接受 <dir>/main.py。"""
    candidates = [root] + [os.path.join(root, d) for d in sorted(os.listdir(root))
                           if os.path.isdir(os.path.join(root, d))]
    for candidate in candidates:
        src = os.path.join(candidate, "src")
        if os.path.isfile(os.path.join(src, "main.py")):
            return src, ""
    for candidate in candidates:
        if os.path.isfile(os.path.join(candidate, "main.py")):
            return candidate, "⚠ 未按约定提供 src/main.py，按该目录作为源码目录评分（提交格式不符）"
    return None, ""


def prepare_submission(path):
    """Return (src_dir, name, layout_note, tempdir_or_None)."""
    if os.path.isdir(path):
        src, note = locate_src(path)
        if src is None:
            fail(f"{path}: 找不到 src/main.py（评分入口约定为 <提交>/src/main.py）")
        return src, os.path.basename(os.path.abspath(path)), note, None
    if os.path.isfile(path) and path.lower().endswith(".zip"):
        tmp = tempfile.mkdtemp(prefix="grade-")
        try:
            safe_extract(path, tmp)
        except ValueError as exc:
            shutil.rmtree(tmp, ignore_errors=True)
            fail(str(exc))
        src, note = locate_src(tmp)
        if src is None:
            top = sorted(os.listdir(tmp))[:20]
            shutil.rmtree(tmp, ignore_errors=True)
            fail(f"{path}: 解压后找不到 src/main.py（顶层内容：{top}）")
        return src, os.path.basename(path)[:-4] or "submission", note, tmp
    fail(f"{path}: 既不是目录也不是 .zip 文件")


# ------------------------------------------------------------------ 模块化探针

def module_files(src_dir):
    return {fn[:-3]: os.path.join(src_dir, fn)
            for fn in sorted(os.listdir(src_dir)) if fn.endswith(".py")}


class _ImportCollector(ast.NodeVisitor):
    """区分模块级导入（导入期执行）与函数内延迟导入（调用期执行）。

    类体导入在类创建时执行，仍算模块级；只有函数/方法体内的导入是延迟的。
    """

    def __init__(self):
        self.func_depth = 0
        self.module_level = []  # (行号, [目标模块名])
        self.lazy = []

    def _visit_func(self, node):
        self.func_depth += 1
        self.generic_visit(node)
        self.func_depth -= 1

    visit_FunctionDef = _visit_func
    visit_AsyncFunctionDef = _visit_func

    def visit_Import(self, node):
        self._record(node, [alias.name.split(".")[0] for alias in node.names])

    def visit_ImportFrom(self, node):
        if node.level:  # 相对导入：from . import x / from .x import y
            targets = [node.module.split(".")[0]] if node.module \
                else [alias.name for alias in node.names]
        elif node.module:
            targets = [node.module.split(".")[0]]
        else:
            targets = []
        self._record(node, targets)

    def _record(self, node, targets):
        entry = (node.lineno, targets)
        (self.module_level if self.func_depth == 0 else self.lazy).append(entry)


def import_graph(src_dir):
    """Return (graph, parse_errors, lazy_edges).

    graph 只含模块级导入的本地边——只有它们会在导入期成环；
    lazy_edges 是函数内延迟导入的本地边 [(模块, 行号, 目标)]，单独报告，
    不参与环检测（延迟导入正是打破导入环的常规手段）。
    """
    modules = module_files(src_dir)
    graph = {name: set() for name in modules}
    errors, lazy_edges = [], []
    for name, path in modules.items():
        try:
            tree = ast.parse(read_text(path))
        except SyntaxError as exc:
            errors.append(f"{name}.py 无法解析：{exc}")
            continue
        collector = _ImportCollector()
        collector.visit(tree)
        for _, targets in collector.module_level:
            for target in targets:
                if target in modules:
                    graph[name].add(target)
        for lineno, targets in collector.lazy:
            for target in targets:
                if target in modules:
                    lazy_edges.append((name, lineno, target))
    return graph, errors, sorted(lazy_edges)


def find_cycles(graph):
    cycles = []
    color = {node: 0 for node in graph}  # 0 未访问 / 1 访问中 / 2 已完成
    stack = []

    def visit(node):
        color[node] = 1
        stack.append(node)
        for nxt in sorted(graph[node]):
            if color[nxt] == 1:
                cycles.append(stack[stack.index(nxt):] + [nxt])
            elif color[nxt] == 0:
                visit(nxt)
        stack.pop()
        color[node] = 2

    for node in sorted(graph):
        if color[node] == 0:
            visit(node)
    return cycles


def reachable(graph, start):
    seen, todo = set(), [start]
    while todo:
        for nxt in graph[todo.pop()]:
            if nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    return seen


def loc_stats(src_dir):
    counts = {name: len(read_text(path).splitlines())
              for name, path in module_files(src_dir).items()}
    total = sum(counts.values())
    top_name, top_count = max(counts.items(), key=lambda kv: kv[1]) if counts else ("", 0)
    share = (top_count / total) if total else 0.0
    return counts, total, top_name, share


def frontend_evidence(src_dir, graph, standard_layout=True):
    """探针③：前端模块能否脱离求值器单独验证。

    返回 (证据行, verdict)，verdict = pass | fail | undetermined；
    undetermined 用于识别不出前端/求值器模块名的情形（命名非常规），此时不扣分。
    """
    modules = module_files(src_dir)
    frontend = [n for n in sorted(modules) if FRONTEND_RE.search(n)]
    evaluators = set(n for n in sorted(modules) if EVAL_RE.search(n))
    entry = "src/main.py" if standard_layout else "main.py（非标准布局）"
    lines = [f"入口 `{entry}` 存在"]
    if not frontend:
        lines.append("未识别到前端阶段模块（文件名含 token/lex/parse/print/read）——未判定，不扣分")
        return lines, "undetermined"
    if not evaluators:
        lines.append("未识别到求值器模块（文件名含 eval/apply/interp）——未判定，不扣分")
        return lines, "undetermined"
    independent = [n for n in frontend if not reachable(graph, n) & evaluators]
    for name in frontend:
        if name in independent:
            lines.append(f"`{name}.py` 不依赖求值器——可单独验证的候选 ✓")
        else:
            lines.append(f"`{name}.py` 间接依赖求值器——不能脱离求值器单独验证")
    return lines, ("pass" if independent else "fail")


# ------------------------------------------------------------------ 自动评分
# 规则以 rubric.md §2–§3 为准；两处必须保持一致。

def score_modularity(module_count, cycles, concentration, frontend_verdict):
    """模块化分（rubric §2），返回 (分数, 明细行)。"""
    if module_count <= 1:
        return 2, ["仅 1 个模块文件 → 按 0–4 档取 2 分"]
    score = 25
    details = []
    if cycles:
        score -= 10
        details.append("探针① 存在模块级环 → −10")
    if concentration:
        score -= 15
        details.append("探针② 最大模块 >60% 行数 → −15")
    if frontend_verdict == "fail":
        score -= 5
        details.append("探针③ 前端模块全部依赖求值器 → −5")
    elif frontend_verdict == "undetermined":
        details.append("探针③ 未判定（模块命名非典型）→ 不扣分")
    if not details:
        details.append("三探针全过")
    return max(score, 0), details


def comment_units(src_dir):
    """注释单元：COMMENT token + 模块/类/函数 docstring，返回 [(相对路径, 行号, 文本)]。"""
    units = []
    for path in source_files(src_dir):
        rel = os.path.relpath(path, src_dir)
        text = read_text(path)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef,
                                     ast.FunctionDef, ast.AsyncFunctionDef)):
                    doc = ast.get_docstring(node)
                    if doc:
                        units.append((rel, getattr(node, "lineno", 1), doc))
        try:
            tokens = tokenize.generate_tokens(io.StringIO(text).readline)
            for tok in tokens:
                if tok.type == tokenize.COMMENT:
                    units.append((rel, tok.start[0], tok.string))
        except (tokenize.TokenError, SyntaxError, IndentationError):
            pass
    return units


def score_comments(src_dir):
    """注释 0/3/5（rubric §3），返回 (分数, "为什么"标记位置, 注释单元总数)。"""
    units = comment_units(src_dir)
    why = [(rel, line) for rel, line, text in units if WHY_MARKERS.search(text)]
    if not units:
        score = 0
    elif len(why) >= 3:
        score = 5
    else:
        score = 3
    return score, why, len(units)


def _target_names(target):
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [n for elt in target.elts for n in _target_names(elt)]
    return []


def single_letter_names(src_dir):
    """单字母的模块级绑定与函数/类名（去重排序），近似"无意义命名"的证据。

    参数与循环变量里的单字母（lambda x、for i）是数学与遍历惯例，不计。
    """
    found = set()
    for path in source_files(src_dir):
        try:
            tree = ast.parse(read_text(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if len(node.name) == 1:
                    found.add(node.name)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                names = [n for t in node.targets for n in _target_names(t)]
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                names = _target_names(node.target)
            else:
                continue
            found.update(n for n in names if len(n) == 1 and n != "_")
    return sorted(found)


def score_naming(src_dir):
    """命名 0/3/5（rubric §3），返回 (分数, 单字母名列表)。"""
    names = single_letter_names(src_dir)
    if len(names) <= 1:
        return 5, names
    if len(names) <= 4:
        return 3, names
    return 0, names


def run_probe(cmd, program, timeout=ROBUSTNESS_TIMEOUT):
    """按 CLI 约定以 stdin 跑一个探针程序，返回 (报错可读?, 明细)。"""
    try:
        proc = subprocess.run(cmd, input=program + "\n", capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"超时（>{timeout}s）"
    except OSError as exc:
        return False, f"无法运行：{exc}"
    stderr, stdout = proc.stderr or "", proc.stdout or ""
    if "Traceback (most recent call last)" in stderr + stdout:
        return False, "裸 Python traceback"
    if proc.returncode == 0:
        return False, "未报错（退出码 0）"
    message = stderr.strip() or stdout.strip()
    if not message:
        return False, f"退出码 {proc.returncode}，无错误信息"
    first = message.splitlines()[0][:80]
    return True, f"可读报错（退出码 {proc.returncode}）：{first}"


def score_robustness(cmd):
    """鲁棒性 0/3/5（rubric §3），返回 (分数, [(探针名, 通过?, 明细)])。"""
    results = []
    readable = 0
    for label, program in ROBUSTNESS_PROBES:
        ok, detail = run_probe(cmd, program)
        results.append((label, ok, detail))
        readable += ok
    if readable >= 2:
        score = 5
    elif readable == 1:
        score = 3
    else:
        score = 0
    return score, results


# ------------------------------------------------------------------ 红线扫描

def hidden_needles(hidden_dir):
    """(组名, 用例行号, 文本) —— 隐藏用例的非注释行，只用于比对。"""
    needles = []
    for fn in sorted(os.listdir(hidden_dir)):
        if not fn.endswith(".scm"):
            continue
        group = fn[:-4]
        text = read_text(os.path.join(hidden_dir, fn))
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped and not stripped.startswith(";") and len(stripped) >= MIN_MATCH_LEN:
                needles.append((group, lineno, stripped))
    return needles


def public_corpus():
    """学生公开可见的全部文本：spec/README/示例/公开用例。

    与公开材料重复的行不可能构成"内嵌隐藏用例"的证据（例如 spec §5 公开的
    (/ -7 2)、(quotient -7 2) 恰好也出现在隐藏用例里），比对前先排除。
    """
    texts = []
    starter = os.path.join(REPO_ROOT, "starter")
    for name in ("spec.md", "README.md"):
        path = os.path.join(starter, name)
        if os.path.isfile(path):
            texts.append(read_text(path))
    example_dir = os.path.join(starter, "example")
    if os.path.isdir(example_dir):
        for fn in sorted(os.listdir(example_dir)):
            if fn.endswith(".scm"):
                texts.append(read_text(os.path.join(example_dir, fn)))
    for fn in sorted(os.listdir(PUBLIC_DIR)):
        if fn.endswith((".scm", ".out")):
            texts.append(read_text(os.path.join(PUBLIC_DIR, fn)))
    return "\n".join(texts)


def source_files(src_dir):
    files = []
    for root, dirs, names in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fn in sorted(names):
            if fn.endswith(".py"):
                files.append(os.path.join(root, fn))
    return files


def red_flag_scan(src_dir, hidden_dir):
    """返回 (flags, stats)；stats = (参与比对的用例行数, 因与公开材料重复而排除的行数)。"""
    flags = []
    all_needles = hidden_needles(hidden_dir)
    corpus = public_corpus()
    needles = [n for n in all_needles if n[2] not in corpus]
    stats = (len(needles), len(all_needles) - len(needles))
    for path in source_files(src_dir):
        text = read_text(path)
        rel = os.path.relpath(path, src_dir)
        lines = text.splitlines()
        hits = {}
        for group, case_line, needle in needles:
            if needle in text:
                idx = next(i for i, line in enumerate(lines, 1) if needle in line)
                hits.setdefault(group, (idx, case_line))
        for group in sorted(hits):
            idx, case_line = hits[group]
            flags.append(f"`{rel}:{idx}` 与隐藏组 `{group}` 第 {case_line} 行文本相同")
        for idx, line in enumerate(lines, 1):
            for pattern in FLAG_PATTERNS:
                if pattern in line:
                    flags.append(f"`{rel}:{idx}` 出现 \"{pattern}\"")
    return flags, stats


# ------------------------------------------------------------------ 报告

def short_name(result_name):
    return result_name[:-4] if result_name.endswith(".scm") else result_name


def render_report(ctx):
    out = [f"# 评分报告：{ctx['name']}", ""]
    out.append(f"- 评分时间：{ctx['timestamp']}")
    out.append(f"- 源码：`{ctx['src_dir']}`{ctx['source_note']}")
    out.append(f"- 命令：`{' '.join(ctx['cmd'])}`")
    out.append("")

    results, failed = ctx["results"], ctx["failed"]
    groups = len(results)
    passed = groups - failed
    if ctx["case_filter"]:
        first = results[0]
        status = "PASS" if first.passed else f"FAIL（{first.summary}）"
        out.append(f"## 单组抽查 `--case={ctx['case_filter']}`：{short_name(first.name)} {status}（不计 60 分）")
    elif ctx["public"]:
        out.append(f"## 公开集自查：{passed}/{groups} 通过（不计分；公开集为提交门槛）")
    else:
        failed_names = [short_name(r.name) for r in results if not r.passed]
        summary = "全过" if not failed_names else "、".join(failed_names)
        out.append(f"## 功能（60）：{5 * passed}/60；未过组：{summary}")
        if groups != 12:
            out.append(f"> 注意：本次只跑了 {groups} 组。")
    out.append("")
    out.append("| 组 | 结果 | 说明 |")
    out.append("|---|---|---|")
    for r in results:
        out.append(f"| {short_name(r.name)} | {'PASS' if r.passed else 'FAIL'} | {r.summary} |")
    out.append("")
    if failed:
        out.append("> 失败细节（diff / stderr，可能含隐藏用例内容）只在评分终端与 "
                   "`build/reports/logs/` 下的日志中；本报告刻意不含。")
        out.append("")

    if ctx["mod_override"]:
        out.append(f"## 模块化（25）：{ctx['mod_score']}（人工改判；自动评 {ctx['mod_auto']}）")
    else:
        out.append(f"## 模块化（25）：{ctx['mod_score']}（工具自动评）")
    out.append("")
    out.append("评分明细：" + "；".join(ctx["mod_details"]))
    out.append("")
    out.append("证据：")
    out.append("")
    out.append("**探针① 依赖图**（模块 → 其本地依赖）：")
    out.append("")
    out.append("```")
    out.extend(ctx["dep_lines"] or ["（无 .py 模块）"])
    out.append("```")
    out.append("")
    if ctx["cycles"]:
        for cycle in ctx["cycles"]:
            out.append(f"- ⚠ 存在循环依赖：{' → '.join(cycle)}")
    else:
        out.append("- 环：无")
    for err in ctx["parse_errors"]:
        out.append(f"- ⚠ {err}")
    for mod, lineno, target in ctx["lazy_edges"]:
        out.append(f"- ℹ 函数内延迟导入：`{mod}.py:{lineno}` → `{target}.py`"
                   "（调用期执行，用于打破导入环，不计入模块级环）")
    out.append("")
    out.append("**探针② 行数分布**：")
    out.append("")
    out.append("```")
    for mod, cnt in sorted(ctx["counts"].items(), key=lambda kv: -kv[1]):
        out.append(f"{mod}.py  {cnt}")
    out.append(f"共计 {ctx['total_lines']} 行，{len(ctx['counts'])} 个模块")
    out.append("```")
    out.append("")
    if ctx["concentration"]:
        out.append(f"- ⚠ 最大模块 `{ctx['top_name']}.py` 占 {ctx['share']:.0%}（> 60%），关键逻辑可能集中")
    else:
        out.append(f"- 最大模块 `{ctx['top_name']}.py` 占 {ctx['share']:.0%}（≤ 60%）")
    if len(ctx["counts"]) <= 2:
        out.append(f"- ⚠ 仅 {len(ctx['counts'])} 个模块文件")
    out.append("")
    out.append("**探针③ 单独验证候选**：")
    out.append("")
    for line in ctx["frontend_lines"]:
        out.append(f"- {line}")
    out.append("")

    if ctx["quality_override"]:
        out.append(f"## 代码规范（15）：{ctx['quality_score']}（人工改判；自动评 {ctx['quality_auto']}）")
    else:
        out.append(f"## 代码规范（15）：{ctx['quality_score']}（工具自动评）")
    out.append("")
    readable = sum(1 for _, ok, _ in ctx["probe_results"] if ok)
    probe_txt = "；".join(f"{label} {'✓' if ok else '✗'}"
                         for label, ok, _ in ctx["probe_results"])
    out.append(f"- 注释 {ctx['comment_score']}/5：注释 / docstring 共 {ctx['comment_total']} 处，"
               f"含“为什么”标记 {ctx['why_count']} 处")
    out.append(f"- 命名 {ctx['naming_score']}/5：单字母命名 {ctx['one_letter_count']} 个（明细见日志）")
    out.append(f"- 鲁棒性 {ctx['robustness_score']}/5：可读报错 {readable}/{len(ctx['probe_results'])} 类"
               f"（{probe_txt}）")
    out.append("")
    out.append("锚点：注释 5=至少 3 处解释\"为什么\"、3=复述代码、0=无或与代码不符；"
               "命名 5=动词/名词自明一致、3=大致可读、0=无意义命名；"
               "鲁棒性 5=非法输入报可读错误且覆盖空表/除零/参数个数 ≥2 类、3=兜底但无定位、0=裸 traceback。")
    out.append("")

    out.append("## ⚠ 待复核红线（记 0 分前须复核并留档：文件 + 行号）")
    out.append("")
    active, dropped = ctx["needle_stats"]
    out.append(f"> 比对覆盖 {active} 条隐藏用例行；与公开材料（spec/README/示例/公开用例）"
               f"重复的 {dropped} 条已排除（公开可得，不构成证据）。")
    out.append("")
    if ctx["flags"]:
        for flag in ctx["flags"]:
            out.append(f"- {flag}")
        out.append("")
        out.append("> 红线仅标记、未自动扣分（功能分仍按用例结果）；"
                   "须第二名评分者复核并留档（文件 + 行号）后决定是否记 0。")
    else:
        out.append("无。")
    out.append("")
    if ctx["public"] or ctx["case_filter"]:
        out.append("## 总分：不计分（抽查 / 自查模式）")
    else:
        out.append(f"## 总分：{ctx['final_score']}/100")
        out.append("")
        out.append("> 三项分数均为工具自动评分（规则见 rubric.md §2–§3）。")
        for note in (ctx["mod_override"], ctx["quality_override"]):
            if note:
                out.append(f"> {note}（改判依据须记入评语）")
    out.append("")
    out.append("评语：__")
    out.append("")
    return "\n".join(out)


def report_path_for(out_dir, name, used):
    """本次运行内不重名（目录与 zip 同名时后者加 _zip）；同名报告覆盖旧文件。"""
    base = name
    if base in used:
        base = name + "_zip"
        i = 2
        while base in used:
            base = f"{name}_zip{i}"
            i += 1
    used.add(base)
    return os.path.join(out_dir, base + ".md")


# ------------------------------------------------------------------ 主流程

def grade_one(path, args, out_dir, used):
    src_dir, name, layout_note, tmp = prepare_submission(path)
    try:
        return _grade_prepared(src_dir, name, layout_note, tmp is not None, args, out_dir, used)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def _grade_prepared(src_dir, name, layout_note, from_zip, args, out_dir, used):
    cases_dir = PUBLIC_DIR if args.public else HIDDEN_DIR
    cmd = shlex.split(args.cmd) if args.cmd else [sys.executable, os.path.join(src_dir, "main.py")]

    print(f"== {name} ==")
    log = []

    def emit(line):
        print(line)
        log.append(line)

    results, failed = run_tests.run_cases(cases_dir, cmd, emit=emit, only=args.case)
    if args.case and not results:
        fail(f"--case={args.case}：没有匹配的用例组")
    groups = len(results)
    passed = groups - failed
    score = 5 * passed

    graph, parse_errors, lazy_edges = import_graph(src_dir)
    counts, total_lines, top_name, share = loc_stats(src_dir)
    dep_lines = []
    for mod in sorted(graph):
        deps = ", ".join(f"{d}.py" for d in sorted(graph[mod])) or "（无）"
        dep_lines.append(f"{mod}.py → {deps}")
    flags, needle_stats = red_flag_scan(src_dir, HIDDEN_DIR)

    cycles = find_cycles(graph)
    concentration = share > CONCENTRATION_THRESHOLD
    frontend_lines, frontend_verdict = frontend_evidence(
        src_dir, graph, standard_layout=not layout_note)
    auto_mod, mod_details = score_modularity(
        len(counts), cycles, concentration, frontend_verdict)
    comment_score, why_units, comment_total = score_comments(src_dir)
    naming_score, one_letter = score_naming(src_dir)
    robustness_score, probe_results = score_robustness(cmd)
    auto_quality = comment_score + naming_score + robustness_score

    for label, ok, detail in probe_results:
        log.append(f"鲁棒性探针[{label}]：{'可读' if ok else '未通过'}——{detail}")
    for rel, line in why_units:
        log.append(f"注释“为什么”标记：{rel}:{line}")
    if one_letter:
        log.append("单字母命名：" + "、".join(one_letter))

    mod_score, quality_score = auto_mod, auto_quality
    mod_override = quality_override = ""
    if args.modularity is not None:
        mod_override = f"模块化人工改判：自动 {auto_mod} → {args.modularity}"
        mod_score = args.modularity
    if args.quality is not None:
        quality_override = f"代码规范人工改判：自动 {auto_quality} → {args.quality}"
        quality_score = args.quality
    final_score = score + mod_score + quality_score

    notes = [n for n in ("zip 提交，已解压到临时目录评分" if from_zip else "", layout_note) if n]
    ctx = {
        "name": name,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "src_dir": src_dir,
        "source_note": ("（" + "；".join(notes) + "）") if notes else "",
        "cmd": cmd,
        "results": results,
        "failed": failed,
        "public": args.public,
        "case_filter": args.case,
        "dep_lines": dep_lines,
        "cycles": cycles,
        "parse_errors": parse_errors,
        "lazy_edges": lazy_edges,
        "counts": counts,
        "total_lines": total_lines,
        "top_name": top_name,
        "share": share,
        "concentration": concentration,
        "frontend_lines": frontend_lines,
        "flags": flags,
        "needle_stats": needle_stats,
        "mod_score": mod_score,
        "mod_auto": auto_mod,
        "mod_details": mod_details,
        "mod_override": mod_override,
        "quality_score": quality_score,
        "quality_auto": auto_quality,
        "quality_override": quality_override,
        "comment_score": comment_score,
        "why_count": len(why_units),
        "comment_total": comment_total,
        "naming_score": naming_score,
        "one_letter_count": len(one_letter),
        "robustness_score": robustness_score,
        "probe_results": probe_results,
        "final_score": final_score,
    }

    base = name
    if args.case:
        base = f"{name}_case{args.case}"
    elif args.public:
        base = f"{name}_public"
    report_path = report_path_for(out_dir, base, used)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(ctx))

    logs_dir = os.path.join(out_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_name = os.path.splitext(os.path.basename(report_path))[0] + ".log"
    with open(os.path.join(logs_dir, log_name), "w", encoding="utf-8") as fh:
        fh.write(f"# {name} 评分日志（可能含隐藏用例内容，勿外传）\n")
        fh.write(f"# 命令：{' '.join(cmd)}\n\n")
        fh.write("\n".join(log) + "\n")

    if args.case:
        first = results[0]
        print(f"抽查 {first.name}: {'PASS' if first.passed else 'FAIL'}；报告 {report_path}")
    elif args.public:
        print(f"公开集 {passed}/{groups}；报告 {report_path}")
    else:
        print(f"总分 {final_score}/100 = 功能 {score}/{groups * 5} + 模块化 {mod_score}/25 "
              f"+ 规范 {quality_score}/15；⚠ 红线 {len(flags)}；报告 {report_path}")
    return {"name": name, "score": score, "groups": groups, "failed": failed,
            "flags": len(flags), "report": report_path,
            "modularity": mod_score, "quality": quality_score, "total": final_score}


def grade_batch(batch_dir, args, out_dir, used):
    entries = sorted(os.listdir(batch_dir))
    infos, skipped = [], []
    for entry in entries:
        path = os.path.join(batch_dir, entry)
        if os.path.isdir(path) or (os.path.isfile(path) and entry.lower().endswith(".zip")):
            infos.append(grade_one(path, args, out_dir, used))
        else:
            skipped.append(entry)

    lines = ["# 批量评分汇总", "",
             f"- 时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
             f"- 提交目录：`{batch_dir}`",
             f"- 提交数：{len(infos)}" + (f"，跳过 {len(skipped)} 项" if skipped else ""),
             "",
             "| 提交 | 功能（60） | 模块化（25） | 代码规范（15） | 总分 | 备注 |",
             "|---|---|---|---|---|---|"]
    for info in infos:
        notes = []
        if info["failed"]:
            notes.append(f"未过 {info['failed']} 组")
        if info["flags"]:
            notes.append(f"⚠ 红线 {info['flags']}，待人工复核")
        lines.append(f"| {info['name']} | {info['score']} | {info['modularity']} | "
                     f"{info['quality']} | {info['total']} | {'；'.join(notes) or '—'} |")
    lines.append("")
    lines.append("> 三项均为工具自动评分（规则见 rubric.md §2–§3）；红线仅标记、不扣分。")
    if skipped:
        lines.append(f"> 已跳过（非目录/非 zip）：{', '.join(skipped)}")
    lines.append("")
    out_path = os.path.join(out_dir, "_summary.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print(f"批量完成：{len(infos)} 份；汇总 {out_path}")
    for info in infos:
        flag = f"  ⚠ 红线 {info['flags']}" if info["flags"] else ""
        print(f"  {info['name']}: {info['score']}/{info['groups'] * 5}{flag}")
    return infos


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", help="提交目录或 .zip")
    parser.add_argument("--batch", metavar="DIR", help="批量：目录下每个子目录/zip 各出一份报告")
    parser.add_argument("--public", action="store_true", help="改跑公开集（自查，不计分）")
    parser.add_argument("--case", metavar="NAME", help="只跑名字含 NAME 的一组（不计 60 分）")
    parser.add_argument("--cmd", metavar="CMD", help="解释器命令（默认 python3 <src>/main.py）")
    parser.add_argument("--out", metavar="DIR", default=DEFAULT_OUT,
                        help="报告输出目录（默认 build/reports）")
    parser.add_argument("--modularity", type=int, metavar="N",
                        help="覆盖自动模块化分（0–25），改判用，依据记入评语")
    parser.add_argument("--quality", type=int, metavar="N",
                        help="覆盖自动代码规范分（0–15），改判用，依据记入评语")
    args = parser.parse_args()

    if bool(args.path) == bool(args.batch):
        parser.error("请给出恰好一个：提交路径，或 --batch <目录>")
    if args.batch and (args.public or args.case
                       or args.modularity is not None or args.quality is not None):
        parser.error("--public / --case / --modularity / --quality 只能用于单个提交")
    if args.modularity is not None and not 0 <= args.modularity <= 25:
        parser.error("--modularity 取值范围 0–25")
    if args.quality is not None and not 0 <= args.quality <= 15:
        parser.error("--quality 取值范围 0–15")

    os.makedirs(args.out, exist_ok=True)
    used = set()
    infos = grade_batch(args.batch, args, args.out, used) if args.batch \
        else [grade_one(args.path, args, args.out, used)]
    sys.exit(1 if any(info["failed"] for info in infos) else 0)


if __name__ == "__main__":
    main()
