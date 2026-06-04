from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelineConfig:
    amap_api_key: str
    raw_dir: Path
    default_city: str = "上海"
    default_merchant_limit: int = 500
    default_dish_limit: int = 5000

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        raw_dir = Path(os.getenv("DATA_PIPELINE_RAW_DIR", "tmp/data_pipeline"))
        return cls(
            amap_api_key=os.getenv("AMAP_API_KEY", ""),
            raw_dir=raw_dir,
            default_city=os.getenv("DATA_PIPELINE_DEFAULT_CITY", "上海"),
            default_merchant_limit=int(os.getenv("DATA_PIPELINE_MERCHANT_LIMIT", "500")),
            default_dish_limit=int(os.getenv("DATA_PIPELINE_DISH_LIMIT", "5000")),
        )
