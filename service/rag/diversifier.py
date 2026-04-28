from __future__ import annotations

from service.rag.models import FusedCandidate


def diversify(candidates: list[FusedCandidate], limit: int, merchant_scoped: bool = False) -> list[FusedCandidate]:
    if merchant_scoped:
        return candidates[:limit]

    selected = []
    seen_dish_names = set()
    merchant_counts: dict[int, int] = {}

    for candidate in candidates:
        dish_name = candidate.facts.get("dish_name")
        merchant_id = candidate.facts.get("merchant_id")
        if dish_name and dish_name in seen_dish_names:
            continue
        if merchant_id is not None and merchant_counts.get(int(merchant_id), 0) >= 1:
            continue
        selected.append(candidate)
        if dish_name:
            seen_dish_names.add(dish_name)
        if merchant_id is not None:
            merchant_counts[int(merchant_id)] = merchant_counts.get(int(merchant_id), 0) + 1
        if len(selected) >= limit:
            return selected

    for candidate in candidates:
        if candidate not in selected:
            selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected
