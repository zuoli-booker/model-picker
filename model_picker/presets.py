"""P1：预设场景（US6）——跳过任务/偏好问答直接生成，为演示和内容创作服务。

预设只预填第 2、3 步（任务类型与偏好）；第 1 步"你手头有哪些模型"仍会询问，
因为策略必须基于用户真实持有的 Key，不能替用户臆造。
"""

from __future__ import annotations

# name → 场景定义
PRESETS: dict[str, dict] = {
    "weekly_report": {
        "name": "周报搭子",
        "desc": "写周报 / 日常问答，均衡优先",
        "tasks": ["writing", "chat"],
        "priority": "balanced",
    },
    "copywriter": {
        "name": "文案写手",
        "desc": "写文案 / 翻译 / 日常问答，质量优先",
        "tasks": ["writing", "translation", "chat"],
        "priority": "quality",
    },
    "coder_helper": {
        "name": "编程助手",
        "desc": "写代码 / 日常问答，质量优先",
        "tasks": ["coding", "chat"],
        "priority": "quality",
    },
    "doc_diver": {
        "name": "长文档钻研",
        "desc": "长文档总结 / 翻译 / 日常问答，质量优先",
        "tasks": ["long_doc", "translation", "chat"],
        "priority": "quality",
    },
    "data_worker": {
        "name": "表格整理",
        "desc": "数据整理 / 写文案 / 日常问答，省钱优先",
        "tasks": ["data_excel", "writing", "chat"],
        "priority": "cost",
    },
}

PRESET_NAMES = tuple(PRESETS)


def get_preset(name: str) -> dict:
    return PRESETS[name]


def format_preset_list() -> str:
    """--list-presets 的展示文本。"""
    lines = ["可用预设场景："]
    for key, p in PRESETS.items():
        lines.append(f"  {key:<14}{p['name']}——{p['desc']}")
    lines.append("用法：python -m model_picker --preset <场景名>")
    return "\n".join(lines)
