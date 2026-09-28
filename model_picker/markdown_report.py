"""P1：Markdown 策略报告 my-strategy.md（US5 的可分享载体）。

人话版策略报告：也是内容运营素材模板（小红书笔记"我的多模型配置"的具象化）。
零依赖：Markdown 用字符串模板拼装。
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .cost import estimate_costs
from .engine import PRIORITIES, Strategy

MARKDOWN_FILENAME = "my-strategy.md"


def _money(x: float | None) -> str:
    if x is None:
        return "—"
    return f"¥{x:.0f}" if abs(x) >= 100 else f"¥{x:.1f}"


def build_markdown(strategy: Strategy, today: str | None = None) -> str:
    today = today or date.today().isoformat()
    lines: list[str] = []
    updated = strategy.meta.get("updated_at", "未知")

    lines += [
        "# 我的多模型使用策略",
        "",
        f"> 由 model-picker 生成于 {today}｜模型数据更新于 {updated}｜完全离线生成，未接触任何 API Key",
        "",
        "## 我的情况",
        "",
        f"- 手头模型：{'、'.join(m.display_name for m in strategy.selected)}",
        f"- 主要场景：{'、'.join(r.task_name for r in strategy.recommendations)}",
        f"- 更看重：{PRIORITIES[strategy.priority]}",
        "",
        "## 策略一览",
        "",
        "| 任务 | 首选 | 备选 | 首选综合分 |",
        "|---|---|---|---|",
    ]
    for rec in strategy.recommendations:
        backup = rec.backup.label() if rec.backup else "—"
        lines.append(f"| {rec.task_name} | {rec.primary.label()} | {backup} | {rec.primary_score:.2f} |")

    lines += ["", "## 每个任务怎么用", ""]
    for rec in strategy.recommendations:
        lines += [f"### {rec.task_name}", ""]
        lines.append(f"- **首选**：{rec.primary.label()} —— LiteLLM 别名 `{rec.task_id}`")
        for i, reason in enumerate(rec.reasons, 1):
            lines.append(f"  {i}. {reason}")
        if rec.backup is not None:
            lines.append(
                f"- **备选**：{rec.backup.label()} —— 别名 `{rec.task_id}_backup`（首选失败自动降级）"
            )
        lines.append("")

    lines += [
        "## 月成本估算",
        "",
        "用量假设（写死注明，只为感知量级，不追求精确）：",
        "",
        "| 档位 | 用量假设 | 本策略月成本 | 全用最贵模型 | 预计节省 |",
        "|---|---|---|---|---|",
    ]
    for row in estimate_costs(strategy):
        baseline = _money(row["baseline"])
        saving = _money(row["saving"])
        if row["saving_pct"] is not None:
            saving += f"（{row['saving_pct']:.0%}）"
        lines.append(
            f"| {row['tier']} | {row['desc']} | {_money(row['cost'])} | {baseline} | {saving} |"
        )
    expensive = next((r["baseline_model"] for r in estimate_costs(strategy) if r["baseline_model"]), None)
    if expensive:
        lines += ["", f"（基线模型：{expensive.label()}，你的清单里最贵的一档）"]

    lines += [
        "",
        "## 接入三步",
        "",
        "1. 在 `model-picker-config.yaml` 注释列出的环境变量里填入你已有的各家 API Key",
        f"2. 运行 `litellm --config model-picker-config.yaml`",
        "3. 你的应用把 `model` 换成任务别名（如 `writing`），即按本策略路由",
        "",
        "## 数据说明",
        "",
        f"- 模型数据更新于 {updated}；来源：{strategy.meta.get('sources', '未知')}",
        "- 分数 0-10 分制；速度为公开测评值；价格为人民币牌价（输入:输出按 3:1 折算混合价）",
        "- 推荐规则固定可查：任务 → 维度权重表 → 偏好调整 → 加权打分，无学习式黑盒",
    ]
    if strategy.meta.get("placeholder_warning"):
        lines.append(f"- ⚠ {strategy.meta['placeholder_warning']}")
    return "\n".join(lines) + "\n"


def write_markdown(strategy: Strategy, path: Path | None = None) -> Path:
    """写入报告到 path（默认当前目录下的 my-strategy.md），返回文件路径。"""
    path = Path(path) if path else Path.cwd() / MARKDOWN_FILENAME
    path.write_text(build_markdown(strategy), encoding="utf-8", newline="\n")
    return path
