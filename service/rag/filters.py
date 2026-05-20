from __future__ import annotations

from langsmith import traceable

from service.rag.models import FusedCandidate, RagQueryPlan


@traceable(name="apply_hard_filters")
def apply_hard_filters(candidates: list[FusedCandidate], plan: RagQueryPlan) -> list[FusedCandidate]:
    filters = plan.must_filters or {}
    exclude_allergens = set(filters.get("exclude_allergens") or [])
    require_available = bool(filters.get("is_available", False))
    merchant_name = filters.get("merchant_name")
    cuisine_types = filters.get("cuisine_types") or []
    required_keywords = filters.get("required_keywords") or []
    forbidden_keywords = filters.get("forbidden_keywords") or []
    budget_max = filters.get("budget_max")
    allowed_source_types = set(plan.source_types) if plan.source_types else None

    kept = []
    for candidate in candidates:
        facts = candidate.facts
        text = _candidate_text(candidate)
        if allowed_source_types and candidate.source_type not in allowed_source_types:
            continue
        if require_available and facts.get("is_available") is not True:
            continue
        if exclude_allergens:
            allergens = facts.get("allergens")
            if allergens and any(item in set(allergens) for item in exclude_allergens):
                continue
        if merchant_name and facts.get("merchant_name") != merchant_name:
            continue
        if budget_max is not None and facts.get("price") is not None:
            if float(facts["price"]) > float(budget_max):
                continue
        if cuisine_types:
            cuisine = str(facts.get("cuisine_type") or "")
            category = str(facts.get("homepage_category") or "")
            if not any(item == cuisine or item in cuisine or item in category for item in cuisine_types):
                continue
        if required_keywords and not all(keyword in text for keyword in required_keywords):
            continue
        if forbidden_keywords and any(keyword in text for keyword in forbidden_keywords):
            continue
        kept.append(candidate)
    return kept


def _candidate_text(candidate: FusedCandidate) -> str:
    facts = candidate.facts or {}
    parts = [candidate.citation]
    parts.extend(str(value) for value in facts.values())
    return " ".join(parts)
