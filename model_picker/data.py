"""数据层：加载 data/models.json。

MVP 阶段数据手动维护（PRD F3）：20 个模型、0-10 分制、价格折合人民币。
本模块只负责"把 JSON 读成 Model 对象"，不打分、不排序。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# 五个能力维度（0-10 分）；速度、价格由实测数据换算，不直接打分
CAPABILITY_DIMS = ("writing", "coding", "long_context", "reasoning", "chinese")

# 清单外模型（用户手动输入）的兜底画像：各维度统一给中性偏下分，并标注"数据缺失"。
# 取 6.0 而非 6.5：低于引擎的 LOW_CONFIDENCE_SCORE(6.5)，让"数据缺失"如实触发补充建议。
FALLBACK_SCORE = 6.0

# 混合价折算假设：输入:输出 = 3:1（轻开发者典型对话场景）
INPUT_OUTPUT_RATIO = 3


@dataclass
class Model:
    """一个模型的数据画像。pricing / speed 为 None 表示"清单外未知模型"。"""

    id: str
    display_name: str
    vendor: str
    origin: str                # "cn" 国内 / "intl" 国际
    litellm_model: str | None  # 如 "deepseek/deepseek-chat"；None=未知模型
    api_key_env: str | None    # 如 "DEEPSEEK_API_KEY"
    pricing: dict | None       # {"input_mtok_cny": 2.0, "output_mtok_cny": 8.0}
    speed: dict | None         # {"tokens_per_sec": 60}
    context_window_k: int | None
    scores: dict               # 五个能力维度，0-10 分
    notes: str = ""

    @property
    def is_known(self) -> bool:
        """False 表示用户手动输入的清单外模型（数据缺失，按通用策略处理）。"""
        return self.pricing is not None and self.speed is not None

    @property
    def blended_price(self) -> float | None:
        """百万 token 混合价（人民币），用于打分与成本估算；未知模型返回 None。"""
        if self.pricing is None:
            return None
        p = self.pricing
        return (p["input_mtok_cny"] * INPUT_OUTPUT_RATIO + p["output_mtok_cny"]) / (
            INPUT_OUTPUT_RATIO + 1
        )

    @property
    def origin_cn(self) -> str:
        return "国内" if self.origin == "cn" else "国际"

    def label(self) -> str:
        """终端 / 报告里的展示标签，如「DeepSeek V4（deepseek-chat）」；id 与展示名相同时不重复。"""
        return f"{self.display_name}（{self.id}）" if self.display_name != self.id else self.display_name


def default_data_path() -> Path:
    """data/models.json 固定在仓库根目录 data/ 下，随包位置解析，不受运行目录影响。"""
    return Path(__file__).resolve().parent.parent / "data" / "models.json"


def load_models(path: Path | None = None) -> tuple[list[Model], dict]:
    """读取模型清单，返回（模型列表, meta 元信息）；文件缺失抛 FileNotFoundError。"""
    path = Path(path) if path else default_data_path()
    if not path.exists():
        raise FileNotFoundError(f"未找到模型数据文件：{path}")
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    models: list[Model] = []
    for item in raw.get("models", []):
        models.append(
            Model(
                id=item["id"],
                display_name=item["display_name"],
                vendor=item["vendor"],
                origin=item["origin"],
                litellm_model=item.get("litellm_model"),
                api_key_env=item.get("api_key_env"),
                pricing=item.get("pricing"),
                speed=item.get("speed"),
                context_window_k=item.get("context_window_k"),
                scores=item.get("scores", {}),
                notes=item.get("notes", ""),
            )
        )
    return models, raw.get("meta", {})


def make_unknown_model(name: str) -> Model:
    """问答中手动输入的清单外模型：数据缺失，按通用策略处理（各维度中性偏下分）。"""
    return Model(
        id=name,
        display_name=name,
        vendor="未知",
        origin="cn",
        litellm_model=None,
        api_key_env=None,
        pricing=None,
        speed=None,
        context_window_k=None,
        scores={d: FALLBACK_SCORE for d in CAPABILITY_DIMS},
        notes="手动输入的清单外模型，能力按通用画像估算，仅供参考",
    )
