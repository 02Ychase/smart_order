from __future__ import annotations

import re
from collections.abc import Iterable

from data_pipeline.models import NormalizedDish, NormalizedMerchant


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().lower())


def dedupe_merchants(merchants: Iterable[NormalizedMerchant]) -> list[NormalizedMerchant]:
    seen: set[tuple[str, str, str]] = set()
    result: list[NormalizedMerchant] = []
    for merchant in merchants:
        key = (normalize_key(merchant.name), normalize_key(merchant.district), normalize_key(merchant.address))
        if key in seen:
            continue
        seen.add(key)
        result.append(merchant)
    return result


def dedupe_dishes(dishes: Iterable[NormalizedDish]) -> list[NormalizedDish]:
    seen: set[tuple[str, str]] = set()
    result: list[NormalizedDish] = []
    for dish in dishes:
        key = (normalize_key(dish.name), normalize_key(dish.cuisine_type))
        if key in seen:
            continue
        seen.add(key)
        result.append(dish)
    return result
