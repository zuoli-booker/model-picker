"""F2 推荐引擎：规则式推荐（硬约束：每条推荐必须可解释，因此不做任何学习式路由）。

打分流程（PRD F2）：
  任务类型 → 能力维度权重表（本项目认知壁垒，PM 维护）
            → 用户偏好调整权重（省钱/质量/快 ×1.5 后归一化）
            → 各维度 0-10 分（能力分 + 速度/价格换算分）
            → 加权求和排序 → 首选 + 备选 + 可解释理由

F1 问答依赖本文件的权重表；打分、首选/备选与可解释理由生成见文件后半部分。
"""

from __future__ import annotations

from dataclasses import dataclass

from .data import CAPABILITY_DIMS, FALLBACK_SCORE, Model

# 七个维度：前五个是能力（0-10 直接打分），速度/价格由实测数据换算
ALL_DIMS = CAPABILITY_DIMS + ("speed", "price")

# 维度中文名（报告与理由展示用）
DIM_CN = {
    "writing": "写作", "coding": "代码", "long_context": "长文本",
    "reasoning": "推理", "chinese": "中文", "speed": "速度", "price": "价格",
}

# 任务类型 → 能力维度权重表（权重合计 = 1；初版由 PM 维护，见 PRD F2-1）
TASKS: dict[str, dict] = {
    "writing": {"name": "写文案/周报", "weights": {
        "writing": 0.30, "long_context": 0.10, "reasoning": 0.15,
        "chinese": 0.25, "speed": 0.10, "price": 0.10}},
    "translation": {"name": "翻译", "weights": {
        "writing": 0.25, "long_context": 0.10, "reasoning": 0.15,
        "chinese": 0.30, "speed": 0.10, "price": 0.10}},
    "long_doc": {"name": "看长文档/总结", "weights": {
        "writing": 0.15, "long_context": 0.35, "reasoning": 0.20,
        "chinese": 0.20, "speed": 0.05, "price": 0.05}},
    "coding": {"name": "写代码/改代码", "weights": {
        "coding": 0.40, "long_context": 0.10, "reasoning": 0.30,
        "chinese": 0.05, "speed": 0.10, "price": 0.05}},
    "data_excel": {"name": "数据整理/Excel", "weights": {
        "writing": 0.15, "coding": 0.25, "long_context": 0.10,
        "reasoning": 0.30, "chinese": 0.10, "speed": 0.05, "price": 0.05}},
    "chat": {"name": "日常问答/查资料", "weights": {
        "writing": 0.20, "long_context": 0.05, "reasoning": 0.20,
        "chinese": 0.20, "speed": 0.20, "price": 0.15}},
}

# 用户偏好（问答第 3 步）：对应维度权重 ×1.5 后重新归一化
PRIORITIES: dict[str, str] = {
    "cost": "省钱（成本优先）",
    "quality": "质量（效果优先）",
    "speed": "快（速度优先）",
    "balanced": "均衡（默认）",
}

PRIORITY_BOOST = 1.5

# 备选"够用线"：该任务综合分 ≥ 7.0 视为够用，取其中价格最低者（PRD F2-4）
ADEQUATE_SCORE = 7.0
# "无合适模型"告警线：首选综合分 < 6.5 视为清单里没有特别适合的（PRD F2-4）
LOW_CONFIDENCE_SCORE = 6.5
# 一条推荐最多展开几个关键维度（理由保持 2-3 句，不堆数字）
MAX_REASON_DIMS = 2


# ---------------------------------------------------------------- 打分


def adjust_weights(weights: dict, priority: str) -> dict:
    """用户偏好调整：省钱→价格、质量→五项能力、快→速度各 ×1.5，再归一化。"""
    adjusted = dict(weights)
    if priority == "cost":
        adjusted["price"] = adjusted.get("price", 0) * PRIORITY_BOOST
    elif priority == "quality":
        for d in CAPABILITY_DIMS:
            if d in adjusted:
                adjusted[d] *= PRIORITY_BOOST
    elif priority == "speed":
        adjusted["speed"] = adjusted.get("speed", 0) * PRIORITY_BOOST
    total = sum(adjusted.values())
    return {d: v / total for d, v in adjusted.items()}


def dimension_scores(model: Model, cheapest_price: float | None) -> dict:
    """把模型换算成七维度 0-10 分。

    - 能力分：data/models.json 的 scores 原样使用
    - 速度分：每 10 tokens/秒 = 1 分，10 分封顶（固定标尺，保证结果可复现）
    - 价格分：以候选集最低混合价为 10 分基准线性换算（越便宜分越高）
    未知模型（清单外手动输入）的速度/价格按中性分处理。
    """
    scores = dict(model.scores)
    tps = model.speed.get("tokens_per_sec") if model.speed else None
    scores["speed"] = min(10.0, tps / 10) if tps else FALLBACK_SCORE
    blended = model.blended_price
    if blended is None or not cheapest_price:
        scores["price"] = FALLBACK_SCORE
    else:
        scores["price"] = min(10.0, 10.0 * cheapest_price / blended)
    return scores


def _score(dim_scores: dict, weights: dict) -> float:
    return sum(weights.get(d, 0.0) * dim_scores.get(d, 0.0) for d in ALL_DIMS)


# ---------------------------------------------------------------- 推荐结果


@dataclass
class Recommendation:
    """单个任务类型的推荐结果（首选 + 备选 + 可解释理由）。"""

    task_id: str
    task_name: str
    weights: dict                                  # 调整并归一化后的权重
    primary: Model
    primary_score: float
    reasons: list[str]
    backup: Model | None = None
    backup_score: float = 0.0
    backup_note: str = ""
    low_confidence: bool = False                   # True=首选分低于告警线
    suggested: Model | None = None                 # 低置信时从全量清单补的建议


@dataclass
class Strategy:
    """完整策略：每个选中任务一条推荐 + 用户输入上下文（报告/配置生成共用）。"""

    recommendations: list[Recommendation]
    priority: str
    selected: list[Model]
    catalog: list[Model]
    meta: dict


def build_strategy(
    selected: list[Model],
    task_ids: list[str],
    priority: str,
    catalog: list[Model],
    meta: dict,
) -> Strategy:
    """对每个选中的任务类型打分排序，生成推荐。价格基准取用户清单里的最低混合价。"""
    known_prices = [m.blended_price for m in selected if m.blended_price is not None]
    cheapest = min(known_prices) if known_prices else None
    recommendations = []
    for task_id in task_ids:
        task = TASKS[task_id]
        weights = adjust_weights(task["weights"], priority)
        scored = sorted(
            ((_score(dimension_scores(m, cheapest), weights), m) for m in selected),
            key=lambda t: t[0],
            reverse=True,
        )
        recommendations.append(
            _make_recommendation(task_id, task["name"], weights, scored, catalog)
        )
    return Strategy(recommendations, priority, selected, catalog, meta)


def _key_dims(weights: dict) -> list[str]:
    """该任务的主角维度（权重最高的前两个能力维度，价格不算"能力"）。"""
    dims = [d for d in sorted(weights, key=lambda d: -weights[d]) if d != "price"]
    return dims[:MAX_REASON_DIMS]


def _suggest_from_catalog(weights: dict, catalog: list[Model], exclude: set[str]) -> Model | None:
    """低置信场景：从全量清单里挑该任务的最优模型（标注"需要新开通 API"）。"""
    prices = [m.blended_price for m in catalog if m.blended_price is not None]
    base = min(prices) if prices else None
    best, best_score = None, -1.0
    for m in catalog:
        if m.id in exclude:
            continue
        s = _score(dimension_scores(m, base), weights)
        if s > best_score:
            best, best_score = m, s
    return best


def _make_recommendation(
    task_id: str,
    task_name: str,
    weights: dict,
    scored: list[tuple[float, Model]],
    catalog: list[Model],
) -> Recommendation:
    """组装一条推荐：首选理由（2-3 句）+ 备选（够用线以上最便宜）+ 低置信补充建议。"""
    top_score, top = scored[0]
    key_dims = _key_dims(weights)

    # 理由第 1 句：关键维度表现 + 是否备选里最高分（对齐 PRD 示例句式）
    dim_parts = []
    for d in key_dims:
        best = max(dimension_scores(m, None)[d] for _, m in scored)  # 能力维度不受价格基准影响
        top_ds = dimension_scores(top, None)
        mark = "，是你的备选里该维度最高分" if top_ds[d] >= best else ""
        dim_parts.append(f"{DIM_CN[d]} {top_ds[d]:.1f}{mark}")
    dim_phrase = "、".join(dim_parts)
    weight_phrase = " / ".join(f"{weights[d]:.0%}" for d in key_dims)
    reasons = [f"推荐 {top.id}：它在该任务最看重的维度表现好——{dim_phrase}"
               f"（该任务权重 {weight_phrase}）。"]

    # 理由第 2 句：价格/速度事实
    if top.blended_price is not None:
        fact = f"百万 token 混合价约 ¥{top.blended_price:.1f}（输入:输出按 3:1 折算）"
    else:
        fact = "该模型不在内置清单，价格未知"
    if top.speed:
        fact += f"，响应速度约 {top.speed['tokens_per_sec']} tokens/秒"
    if top.notes:
        fact += f"；备注：{top.notes}"
    reasons.append(fact + "。")

    # 低置信：清单里没有特别适合的 → 从全量清单补建议（PRD F2-4）
    low_confidence = top_score < LOW_CONFIDENCE_SCORE
    suggested = None
    if low_confidence:
        suggested = _suggest_from_catalog(weights, catalog, {m.id for _, m in scored})
        advice = (f"建议考虑补充 {suggested.label()}（需要新开通 API）。" if suggested else "")
        reasons.append(
            f"⚠ 你的手头模型里没有特别适合「{task_name}」的"
            f"（综合分不足 {LOW_CONFIDENCE_SCORE}）。{advice}"
        )

    # 备选：够用线（≥7.0）以上价格最低的；够用线无人则退而取次高分
    backup, backup_score, backup_note = None, 0.0, ""
    adequate = [(s, m) for s, m in scored[1:] if s >= ADEQUATE_SCORE]
    if adequate:
        def _price_key(item: tuple[float, Model]):
            bp = item[1].blended_price
            return (bp is None, bp if bp is not None else 0.0)

        backup_score, backup = min(adequate, key=_price_key)
        backup_note = f"够用线（≥{ADEQUATE_SCORE}）以上、你清单里价格最低的选项"
    elif len(scored) > 1:
        backup_score, backup = scored[1]
        backup_note = f"与首选有差距（够用线 {ADEQUATE_SCORE} 以下），仅供参考"

    return Recommendation(
        task_id=task_id,
        task_name=task_name,
        weights=weights,
        primary=top,
        primary_score=top_score,
        reasons=reasons,
        backup=backup,
        backup_score=backup_score,
        backup_note=backup_note,
        low_confidence=low_confidence,
        suggested=suggested,
    )
