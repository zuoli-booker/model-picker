"""命令行入口：python -m model_picker [--preset 场景名] [--list-presets]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .data import default_data_path, load_models
from .engine import build_strategy
from .presets import PRESET_NAMES, format_preset_list
from .quiz import run_quiz
from .report import print_costs, print_epilogue, print_strategy
from .yaml_gen import CONFIG_FILENAME, write_config


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="model-picker",
        description="回答几个问题，生成可解释的大模型使用策略和可直接使用的 LiteLLM 配置",
    )
    parser.add_argument(
        "--preset",
        help=f"预设场景（{', '.join(PRESET_NAMES)}），跳过任务与偏好问答",
    )
    parser.add_argument("--list-presets", action="store_true", help="列出所有预设场景后退出")
    parser.add_argument("--version", action="version", version=f"model-picker {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list_presets:
        print(format_preset_list())
        return 0
    if args.preset and args.preset not in PRESET_NAMES:
        print(f"未知预设场景：{args.preset}\n{format_preset_list()}", file=sys.stderr)
        return 2

    try:
        catalog, meta = load_models(default_data_path())
    except FileNotFoundError as e:
        print(f"数据文件缺失：{e}\n请确认 data/models.json 与 model_picker 包同级（见 README 安装部分）。",
              file=sys.stderr)
        return 1

    print("=" * 60)
    print(f"model-picker v{__version__} —— 帮你决定「接哪个模型 + 帮你配好」")
    print("完全离线运行，不接触你的任何 API Key（BYOK）")
    print("=" * 60)

    answers = run_quiz(catalog, preset_name=args.preset)
    if answers is None:
        print("\n已退出，未生成任何文件。")
        return 0

    strategy = build_strategy(
        answers.models, answers.task_ids, answers.priority, catalog, meta
    )
    print_strategy(strategy)
    print_costs(strategy)
    config_path = write_config(strategy, Path.cwd() / CONFIG_FILENAME)
    print_epilogue(
        [(config_path.name, f"LiteLLM 配置，运行：litellm --config {config_path.name}")],
        meta,
    )
    print("\n（Markdown 策略报告开发中，下一步接入……）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
