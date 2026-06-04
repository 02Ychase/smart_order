from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from data_pipeline.models import RawDish


def iter_menustat_csv(path: str | Path, *, limit: int) -> Iterable[RawDish]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        yielded = 0
        for row in reader:
            name = (row.get("item_name") or row.get("Item Name") or row.get("name") or "").strip()
            if not name:
                continue
            restaurant = (row.get("restaurant") or row.get("Restaurant") or "").strip()
            category = (row.get("food_category") or row.get("Food Category") or "").strip()
            calories = (row.get("calories") or row.get("Calories") or "").strip()
            description_parts = [part for part in [restaurant, category, f"{calories} calories" if calories else ""] if part]
            yielded += 1
            yield RawDish(
                source="menustat",
                source_id=f"{restaurant}:{name}" if restaurant else name,
                name=name[:128],
                description="; ".join(description_parts),
                ingredients=[],
                tags=[part for part in [restaurant, category] if part],
                cuisine_type=category,
                price=None,
                raw=dict(row),
            )
            if yielded >= limit:
                break
