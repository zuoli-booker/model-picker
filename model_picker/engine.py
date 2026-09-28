"""F2 推荐引擎：规则式推荐（硬约束：每条推荐必须可解释，因此不做任何学习式路由）。

打分流程（PRD F2）：
  任务类型 → 能力维度权重表（本项目认知壁垒，PM 维护）
            → 用户偏好调整权重（省钱/质量/快 ×1.5 后归一化）
            → 各维度 0-10 分（能力分 + 速度/价格换算分）
            → 加权求和排序 → 首选 + 备选 + 可解释理由

本文件先落地权重表与常量（F1 问答流程依赖）；打分与理由生成在后续提交补齐。
"""

from __future__ import annotations

# 七个维度：前五个是能力（0-10 直接打分），速度/价格由实测数据换算
CAPABILITY_DIMS = ("writing", "coding", "long_context", "reasoning", "chinese")
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
