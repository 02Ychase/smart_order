from __future__ import annotations

from service.rag.models import FusedCandidate, RagQueryPlan


def apply_hard_filters(candidates: list[FusedCandidate], plan: RagQueryPlan) -> list[FusedCandidate]:
    filters = plan.must_filters or {}
    exclude_allergens = set(filters.get("exclude_allergens") or [])
    require_available = bool(filters.get("is_available", False))
    merchant_name = filters.get("merchant_name")

    kept = []
    for candidate in candidates:
        facts = candidate.facts
        if require_available and facts.get("is_available") is not True:
            continue
        if exclude_allergens:
            allergens = facts.get("allergens")
            if allergens is None or any(item in set(allergens) for item in exclude_allergens):
                continue
        if merchant_name and facts.get("merchant_name") != merchant_name:
            continue
        kept.append(candidate)
    return kept
