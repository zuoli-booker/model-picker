"""P1：月成本估算（US5）。

三档用量假设写死并注明（见 USAGE_TIERS），只为让用户感知"量级"与"节省额"，
不追求精确；基线 = 全用清单里最贵的模型（PRD F4-4）。
"""

from __future__ import annotations

from .data import INPUT_OUTPUT_RATIO, Model
from .engine import Strategy

# 三档用量假设（写死；README 与 md 报告使用同一份假设并注明）
USAGE_TIERS: dict[str, dict] = {
    "轻度": {"monthly_tokens": 150_000, "desc": "每天约 5 次对话，每次约 1000 tokens"},
    "中度": {"monthly_tokens": 1_200_000, "desc": "每天约 20 次对话，每次约 2000 tokens"},
    "重度": {"monthly_tokens": 7_200_000, "desc": "每天约 80 次对话，每次约 3000 tokens"},
}

# 输入 token 占比，与混合价折算口径一致（输入:输出 = 3:1 → 0.75）
INPUT_SHARE = INPUT_OUTPUT_RATIO / (INPUT_OUTPUT_RATIO + 1)


def monthly_cost(model: Model, tokens: float) -> float | None:
    """给定月 token 量的月成本（人民币）；未知模型返回 None。"""
    if model.pricing is None:
        return None
    p = model.pricing
    per_token = (INPUT_SHARE * p["input_mtok_cny"]
                 + (1 - INPUT_SHARE) * p["output_mtok_cny"]) / 1_000_000
    return tokens * per_token


def _format_tokens(n: int) -> str:
    """150000 → 15 万；1200000 → 120 万；7200000 → 720 万。"""
    return f"{n / 10000:.0f} 万" if n >= 10000 else str(n)


def estimate_costs(strategy: Strategy) -> list[dict]:
    """按三档估算每行：本策略月成本 vs 全用最贵模型的基线与节省额。"""
    known = [m for m in strategy.selected if m.pricing is not None]
    expensive = max(known, key=lambda m: m.blended_price, default=None)
    n_tasks = max(1, len(strategy.recommendations))
    rows = []
    for tier_name, tier in USAGE_TIERS.items():
        per_task = tier["monthly_tokens"] / n_tasks
        total, has_unknown = 0.0, False
        for rec in strategy.recommendations:
            cost = monthly_cost(rec.primary, per_task)
            if cost is None:
                has_unknown = True
            else:
                total += cost
        baseline = monthly_cost(expensive, tier["monthly_tokens"]) if expensive else None
        saving = None
        if baseline is not None and not has_unknown:
            saving = baseline - total
        rows.append({
            "tier": tier_name,
            "tokens": tier["monthly_tokens"],
            "tokens_label": _format_tokens(tier["monthly_tokens"]),
            "desc": tier["desc"],
            "cost": None if has_unknown else total,
            "baseline": baseline,
            "baseline_model": expensive,
            "saving": saving,
            "saving_pct": (saving / baseline) if (saving is not None and baseline) else None,
        })
    return rows
