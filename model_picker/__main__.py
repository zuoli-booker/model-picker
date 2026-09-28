"""命令行入口骨架（commit 1：先跑通数据加载，问答与生成在后续提交补齐）。"""

from __future__ import annotations

import sys

from . import __version__
from .data import default_data_path, load_models


def main(argv: list[str] | None = None) -> int:
    print(f"model-picker v{__version__}（开发中）")
    try:
        catalog, meta = load_models(default_data_path())
    except FileNotFoundError as e:
        print(f"数据文件缺失：{e}", file=sys.stderr)
        return 1
    print(f"已加载 {len(catalog)} 个模型数据（更新于 {meta.get('updated_at', '未知')}）。")
    print("骨架就绪，问答流程开发中……")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
