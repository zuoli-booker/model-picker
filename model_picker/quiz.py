"""F1 交互问答流程（4 步，每步可回退）。

全中文、编号勾选，用户不需要记任何命令参数（US1）。
每步输入规则：
  多选步骤    输入编号，逗号/空格分隔；输入 q 退出
  确认步骤    回车=生成；输入 1/2/3 回退到对应步骤修改；输入 q 退出
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import presets
from .data import Model, make_unknown_model
from .engine import PRIORITIES, TASKS

STEPS_TOTAL = 4
LINE = "─" * 60
QUIT_WORDS = ("q", "quit", "exit")
_LETTER_TO_PRIORITY = {"A": "cost", "B": "quality", "C": "speed", "D": "balanced"}


class Quit(Exception):
    """用户主动退出（输入 q / Ctrl+C / 输入流结束）。"""


@dataclass
class Answers:
    """用户四步问答的结果。models 含手动输入的清单外模型（按通用策略处理）。"""

    models: list[Model]
    task_ids: list[str]
    priority: str


def _input(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        # 管道输入结束（如测试时的 echo | ...）或 Ctrl+C：视为退出
        raise Quit from None


def _parse_multi(raw: str, n: int) -> list[int] | None:
    """解析多选输入，返回升序去重的合法编号；非法返回 None。"""
    parts = [p for p in re.split(r"[,，、\s]+", raw) if p]
    if not parts:
        return None
    idxs = []
    for p in parts:
        if not p.isdigit() or not (1 <= int(p) <= n):
            return None
        idxs.append(int(p))
    return sorted(set(idxs))


# ---------------------------------------------------------------- 第 1 步


def _ask_models(catalog: list[Model]) -> list[Model] | None:
    """第 1 步：手头有哪些模型的 API。支持手动输入清单外模型。"""
    print(LINE)
    print("第 1 步 / 共 4 步：你手头有哪些模型的 API？")
    print("（输入编号多选，如 1,3,5；输入 m 手动补充清单外模型；q 退出）")
    print(LINE)
    for i, m in enumerate(catalog, 1):
        price = f"¥{m.blended_price:.1f}/百万tok混价" if m.blended_price else "价格未知"
        ctx = f"{m.context_window_k}k 上下文" if m.context_window_k else "上下文未知"
        print(f"  {i:>3}. {m.display_name}（{m.vendor}）  {price}  {ctx}")
    raw = _input("\n你的选择：")
    if raw.lower() in QUIT_WORDS:
        raise Quit
    if raw.lower() == "m":
        names = _input("请输入清单外模型名（多个用逗号分隔）：")
        if not names:
            print("未输入模型名，请重新选择。\n")
            return _ask_models(catalog)
        unknown = [make_unknown_model(n) for n in re.split(r"[,，、\s]+", names) if n]
        print("已加入：" + "、".join(m.display_name for m in unknown) + "（数据缺失，按通用策略处理）")
        return unknown
    idxs = _parse_multi(raw, len(catalog))
    if not idxs:
        print("输入无效：请输入 1-%d 的编号（逗号分隔）。\n" % len(catalog))
        return _ask_models(catalog)
    return [catalog[i - 1] for i in idxs]


# ---------------------------------------------------------------- 第 2 步


def _ask_tasks(defaults: list[str] | None = None) -> list[str]:
    """第 2 步：主要用 AI 干什么（6 类任务多选）。"""
    print(LINE)
    print("第 2 步 / 共 4 步：你主要用 AI 干什么？（多选）")
    print(LINE)
    task_ids = list(TASKS)
    for i, tid in enumerate(task_ids, 1):
        mark = "（默认已选）" if defaults and tid in defaults else ""
        print(f"  {i}. {TASKS[tid]['name']}{mark}")
    hint = f"（直接回车 = {'、'.join(TASKS[t]['name'] for t in defaults)}）" if defaults else ""
    raw = _input(f"\n你的选择{hint}：")
    if raw.lower() in QUIT_WORDS:
        raise Quit
    if not raw and defaults:
        return list(defaults)
    idxs = _parse_multi(raw, len(task_ids))
    if not idxs:
        print("输入无效：请输入 1-%d 的编号（逗号分隔）。\n" % len(task_ids))
        return _ask_tasks(defaults)
    return [task_ids[i - 1] for i in idxs]


# ---------------------------------------------------------------- 第 3 步


def _ask_priority(default: str = "balanced") -> str:
    """第 3 步：更看重什么（单选，A 省钱 / B 质量 / C 快 / D 均衡默认）。"""
    print(LINE)
    print("第 3 步 / 共 4 步：你更看重什么？（单选）")
    print(LINE)
    for k, label in (("A", "省钱（成本优先）"), ("B", "质量（效果优先）"),
                     ("C", "快（速度优先）"), ("D", "均衡（默认）")):
        mark = "（当前）" if default == _LETTER_TO_PRIORITY[k] else ""
        print(f"  {k} {label}{mark}")
    raw = _input("\n你的选择（回车 = 当前选项）：").lower()
    if raw in QUIT_WORDS:
        raise Quit
    mapping = {"a": "cost", "b": "quality", "c": "speed", "d": "balanced", "": default}
    if raw not in mapping:
        print("输入无效：请输入 A/B/C/D。\n")
        return _ask_priority(default)
    return mapping[raw]


# ---------------------------------------------------------------- 第 4 步


def _print_summary(models: list[Model], task_ids: list[str], priority: str) -> None:
    print(LINE)
    print("第 4 步 / 共 4 步：确认你的选择")
    print(LINE)
    names = "、".join(m.display_name for m in models[:8]) + ("等 %d 个" % len(models) if len(models) > 8 else "")
    print(f"  手头模型（{len(models)}）：{names}")
    print(f"  主要任务（{len(task_ids)}）：" + "、".join(TASKS[t]["name"] for t in task_ids))
    print(f"  优先方向：{PRIORITIES[priority]}")


def run_quiz(catalog: list[Model], preset_name: str | None = None) -> Answers | None:
    """执行 4 步问答。返回 Answers；用户主动退出时返回 None。"""
    preset = presets.get_preset(preset_name) if preset_name else None
    if preset:
        print(f"\n已加载预设场景「{preset['name']}」（{preset['desc']}）："
              "只需回答第 1 步，确认摘要后即可生成；输入 2/3 也可回退修改。")
    step, models, task_ids, priority = 1, [], [], "balanced"
    if preset:
        task_ids, priority = list(preset["tasks"]), preset["priority"]
    try:
        while True:
            if step == 1:
                models = _ask_models(catalog)
                # 使用预设时跳过第 2、3 步，直达确认；回退仍可进去改
                step = 4 if preset else 2
            elif step == 2:
                task_ids = _ask_tasks(task_ids if preset else None)
                step = 3
            elif step == 3:
                priority = _ask_priority(priority)
                step = 4
            else:
                _print_summary(models, task_ids, priority)
                action = _input("\n确认生成？[回车]=生成，输入 1/2/3 回退修改，q=退出：").lower()
                if action in ("", "y", "yes"):
                    return Answers(models=models, task_ids=task_ids, priority=priority)
                if action in QUIT_WORDS:
                    return None
                if action in ("1", "2", "3"):
                    step = int(action)
                    continue
                print("输入无效：请回车生成，输入 1/2/3 回退，或输入 q 退出。")
    except Quit:
        return None
