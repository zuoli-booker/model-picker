"""F4-1 终端报告 + P1 成本估算展示（US3/US5 的呈现层）。

全中文；表格用东亚字符宽度对齐（unicodedata.east_asian_width），保证 macOS/Windows 终端可读。
"""

from __future__ import annotations

import unicodedata

from .cost import estimate_costs
from .engine import DIM_CN, PRIORITIES, Strategy, Recommendation

LINE = "=" * 60
THIN = "─" * 60


def _width(text: str) -> int:
    """显示宽度：中文/全角符号算 2，ASCII 算 1。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _width(text))


def _join_models(models, limit: int = 8) -> str:
    names = [m.display_name for m in models[:limit]]
    if len(models) > limit:
        names.append(f"等 {len(models)} 个")
    return "、".join(names)


def _top_weight_dims(rec: Recommendation, n: int = 3) -> str:
    dims = [d for d in sorted(rec.weights, key=lambda d: -rec.weights[d]) if d != "price"][:n]
    return " · ".join(f"{DIM_CN[d]} {rec.weights[d]:.0%}" for d in dims)


def print_strategy(strategy: Strategy) -> None:
    """完整终端报告：你的选择 → 按任务推荐表 + 理由 → 月成本估算。"""
    print()
    print(LINE)
    print("  你的多模型使用策略")
    print(LINE)

    # 你的选择
    print("【你的选择】")
    print(f"  手头模型（{len(strategy.selected)}）：{_join_models(strategy.selected)}")
    print("  主要任务：" + "、".join(r.task_name for r in strategy.recommendations))
    print(f"  优先方向：{PRIORITIES[strategy.priority]}")

    # 按任务推荐
    print()
    print("【按任务的推荐】")
    for rec in strategy.recommendations:
        print(THIN)
        print(f"  {rec.task_name}    （权重侧重：{_top_weight_dims(rec)}）")
        print(f"  ▶ 首选：{rec.primary.label()}    综合分 {rec.primary_score:.2f}")
        for reason in rec.reasons:
            print(f"      {reason}")
        if rec.backup is not None:
            print(f"  ○ 备选：{rec.backup.label()}    综合分 {rec.backup_score:.2f}（{rec.backup_note}）")
        else:
            print("  ○ 备选：无（你的清单里没有其他够用的模型）")
    print(THIN)


def _money(x: float) -> str:
    """金额格式：大额取整，小额保留一位，避免 ¥1/月 这种丢失精度的显示。"""
    return f"¥{x:.0f}" if abs(x) >= 100 else f"¥{x:.1f}"


def print_costs(strategy: Strategy) -> None:
    """月成本估算表（US5）：三档假设 + 对比"全用最贵模型"的节省额。"""
    rows = estimate_costs(strategy)
    print()
    print("【月成本估算】（三档假设，写死注明；只为感知量级，不追求精确）")
    for row in rows:
        print(f"  {row['desc']}")
    print("  " + "-" * 56)
    header = _pad("  档位", 12) + _pad("本策略月成本", 14) + _pad("全用最贵模型", 14) + "预计节省"
    print(header)
    for row in rows:
        cost = _money(row["cost"]) if row["cost"] is not None else "无法估算（含清单外模型）"
        baseline = _money(row["baseline"]) if row["baseline"] is not None else "—"
        saving = (f"{_money(row['saving'])}（{row['saving_pct']:.0%}）"
                  if row["saving"] is not None else "—")
        print(_pad("  " + row["tier"], 12) + _pad(cost, 14) + _pad(baseline, 14) + saving)
    expensive = next((r["baseline_model"] for r in rows if r["baseline_model"]), None)
    if expensive:
        print(f"  （基线模型：{expensive.label()}，你的清单里最贵的一档）")
    print("  假设：输入:输出 = 3:1；各任务均摊月用量；价格为人民币牌价。")


def print_epilogue(files: list[tuple[str, str]], meta: dict) -> None:
    """结尾：生成了哪些文件 + 数据来源说明（可解释性不止于推荐本身）。"""
    print()
    print("【生成的文件】")
    for path, desc in files:
        print(f"  - {path} —— {desc}")
    print()
    print("【数据说明】")
    print(f"  模型数据更新于 {meta.get('updated_at', '未知')}；来源：{meta.get('sources', '未知')}")
    if meta.get("placeholder_warning"):
        print(f"  ⚠ {meta['placeholder_warning']}")
    print("  推荐规则固定可查：每任务的维度权重表在 docs/04-MVP产品需求文档-model-picker.md（F2）。")
