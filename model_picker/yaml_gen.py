"""F4-2：生成 LiteLLM 配置 model-picker-config.yaml（US4，P0）。

零第三方依赖：YAML 用字符串模板拼装，不引 PyYAML（PRD 非功能需求）。
配置设计：
  - 每个任务别名一条 model_list 条目，litellm_params.model 指向首选模型
  - 备选模型生成 <task>_backup 别名，并在 router_settings.fallbacks 声明主备_backup 关系
  - API Key 一律走 os.environ/ 环境变量（BYOK：本工具不碰任何 Key）
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .engine import Strategy, TASKS

CONFIG_FILENAME = "model-picker-config.yaml"


def build_config_yaml(strategy: Strategy, today: str | None = None) -> str:
    today = today or date.today().isoformat()
    lines: list[str] = []

    # 文件头：生成信息 + 使用三步
    lines += [
        "# ============================================================",
        f"# 由 model-picker 生成于 {today} —— 可解释的多模型使用策略",
        "# 用法三步：",
        "#   1. 在下方注释列出的环境变量里填入你已有的各家 API Key",
        "#      （BYOK：本工具不接触、不存储任何 Key）",
        f"#   2. litellm --config {CONFIG_FILENAME}",
        "#   3. 你的应用把 model 换成任务别名（writing / coding / ...）即按本策略路由",
        "# ============================================================",
        "model_list:",
    ]

    fallbacks: list[tuple[str, str]] = []
    for rec in strategy.recommendations:
        primary, backup = rec.primary, rec.backup
        if primary.litellm_model:
            lines.append(f"  # {rec.task_name} —— 首选：{primary.label()}")
            lines += [
                f"  - model_name: {rec.task_id}",
                "    litellm_params:",
                f"      model: {primary.litellm_model}",
                f"      api_key: os.environ/{primary.api_key_env}",
            ]
        else:
            # 清单外模型：无法确定 LiteLLM provider 串，输出注释块让用户自己补
            lines += [
                f"  # {rec.task_name} —— 首选是你手动输入的「{primary.display_name}」（不在内置清单），",
                "  # 请自行补全下面的条目（注意缩进）：",
                f"  # - model_name: {rec.task_id}",
                "  #   litellm_params:",
                "  #     model: <你的 provider/model 串，参考 litellm 文档>",
                "  #     api_key: os.environ/<YOUR_API_KEY_ENV>",
            ]
        if backup is not None and backup.litellm_model and backup.id != primary.id:
            lines.append(f"  # {rec.task_name} —— 备选（fallback）：{backup.label()}")
            lines += [
                f"  - model_name: {rec.task_id}_backup",
                "    litellm_params:",
                f"      model: {backup.litellm_model}",
                f"      api_key: os.environ/{backup.api_key_env}",
            ]
            fallbacks.append((rec.task_id, f"{rec.task_id}_backup"))

    # 路由设置：fallbacks 声明主备关系（首选失败自动降级到备选）
    lines += [
        "router_settings:",
        "  routing_strategy: simple-shuffle",
        "  num_retries: 2",
    ]
    if fallbacks:
        lines.append("  fallbacks:")
        for main, backup in fallbacks:
            lines.append(f"    - {main}: [{backup}]")

    # 文件尾：任务别名对照 + 数据来源
    lines += [
        "",
        "# ============================================================",
        "# 任务别名对照（应用侧 model 参数填别名）：",
    ]
    for rec in strategy.recommendations:
        lines.append(f"#   {rec.task_id:<15}{rec.task_name}")
    updated = strategy.meta.get("updated_at", "未知")
    lines.append(f"# 数据来源：data/models.json（更新于 {updated}）")
    if strategy.meta.get("placeholder_warning"):
        lines.append(f"# ⚠ {strategy.meta['placeholder_warning']}")
    lines.append("# ============================================================")
    return "\n".join(lines) + "\n"


def write_config(strategy: Strategy, path: Path | None = None) -> Path:
    """写入配置到 path（默认当前目录下的 model-picker-config.yaml），返回文件路径。"""
    path = Path(path) if path else Path.cwd() / CONFIG_FILENAME
    path.write_text(build_config_yaml(strategy), encoding="utf-8", newline="\n")
    return path
