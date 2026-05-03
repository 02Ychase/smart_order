from __future__ import annotations

from service.rag.models import FusedCandidate, RagQueryPlan


class WeightedReranker:
    def rerank(
        self,
        candidates: list[FusedCandidate],
        original_query: str,
        query_plan: RagQueryPlan | None = None,
        memories: list[dict] | None = None,
    ) -> list[FusedCandidate]:
        should = (query_plan.should_filters if query_plan else {}) or {}
        should_cuisine = should.get("cuisine_types") or []
        should_flavors = should.get("flavor_preferences") or []

        for candidate in candidates:
            candidate.constraint_match = _calc_constraint_match(candidate, should_cuisine, should_flavors)
            user_pref_score = _calc_user_preference_match(candidate, memories or [])
            candidate.facts["user_preference_match"] = user_pref_score

            merchant_rating = float(candidate.facts.get("merchant_rating") or 0.0) / 5.0
            business_boost = 1.0 if candidate.facts.get("is_recommended") else 0.0

            candidate.final_score = (
                0.30 * candidate.dense_score
                + 0.20 * candidate.lexical_score
                + 0.20 * candidate.constraint_match
                + 0.10 * merchant_rating
                + 0.10 * business_boost
                + 0.10 * user_pref_score
            )
        return sorted(candidates, key=lambda item: item.final_score, reverse=True)


def _calc_constraint_match(candidate: FusedCandidate, cuisine_types: list[str], flavor_prefs: list[str]) -> float:
    if not cuisine_types and not flavor_prefs:
        return 1.0

    hits = 0
    total = 0
    facts = candidate.facts

    if cuisine_types:
        total += 1
        cuisine = str(facts.get("cuisine_type") or "")
        category = str(facts.get("homepage_category") or "")
        combined = f"{cuisine} {category}"
        if any(item in combined for item in cuisine_types):
            hits += 1

    if flavor_prefs:
        total += 1
        flavor_text = " ".join([
            str(facts.get("flavor_profile") or ""),
            str(facts.get("description") or ""),
            str(facts.get("dish_name") or ""),
            str(facts.get("name") or ""),
        ])
        if any(pref in flavor_text for pref in flavor_prefs):
            hits += 1

    if total == 0:
        return 1.0
    return 0.3 + 0.7 * (hits / total)


def _calc_user_preference_match(candidate: FusedCandidate, memories: list[dict]) -> float:
    if not memories:
        return 0.0

    facts = candidate.facts
    candidate_text = " ".join(
        str(facts.get(k, ""))
        for k in ("cuisine_type", "flavor_profile", "dish_name", "name",
                   "merchant_name", "description", "homepage_category")
    )

    score = 0.0
    weight_sum = 0.0
    for mem in memories:
        content = str(mem.get("content", ""))
        confidence = float(mem.get("confidence", 0.5))
        if not content:
            continue
        weight_sum += confidence
        if _text_overlaps(content, candidate_text):
            score += confidence

    if weight_sum == 0:
        return 0.0
    return score / weight_sum


def _text_overlaps(memory_content: str, candidate_text: str) -> bool:
    keywords = ["湘菜", "川菜", "粤菜", "鲁菜", "苏菜", "闽菜", "浙菜", "徽菜",
                "辣", "麻", "酸", "甜", "苦", "咸", "清淡", "香", "鲜",
                "面", "粉", "饭", "汤", "锅", "煲", "烧", "烤", "蒸", "炒",
                "鸡", "鸭", "鱼", "虾", "蟹", "牛", "羊", "猪",
                "咖啡", "茶", "奶茶", "甜点", "蛋糕",
                "素食", "清真"]
    for kw in keywords:
        if kw in memory_content and kw in candidate_text:
            return True
    return False
