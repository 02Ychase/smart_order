from __future__ import annotations

from service.rag.models import FusedCandidate


def diversify(
    candidates: list[FusedCandidate],
    limit: int,
    merchant_scoped: bool = False,
    max_per_merchant: int = 2,
) -> list[FusedCandidate]:
    """Diversify candidates by dish name and per-merchant count.

    First pass: collect candidates with unique dish names, respecting the
    per-merchant cap. Second pass: fill remaining slots with any unseen
    candidates from the original list.

    Args:
        candidates: Fused candidates in ranked order.
        limit: Maximum number of candidates to return.
        merchant_scoped: When True, use at least 3 dishes per merchant
            (for queries like "what does Restaurant X have?").
        max_per_merchant: Maximum dishes from the same merchant (default 2).
    """
    if not candidates:
        return []

    # Merchant-scoped queries get a higher per-merchant allowance.
    if merchant_scoped:
        max_per_merchant = max(max_per_merchant, 3)

    selected: list[FusedCandidate] = []
    seen_dish_names: set[str] = set()
    merchant_counts: dict[int, int] = {}

    for candidate in candidates:
        dish_name = candidate.facts.get("dish_name")
        merchant_id = candidate.facts.get("merchant_id")
        if dish_name and dish_name in seen_dish_names:
            continue
        if merchant_id is not None and merchant_counts.get(int(merchant_id), 0) >= max_per_merchant:
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
