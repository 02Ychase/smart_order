from __future__ import annotations

from service.rag.models import FusedCandidate


class WeightedReranker:
    def rerank(self, candidates: list[FusedCandidate], original_query: str) -> list[FusedCandidate]:
        for candidate in candidates:
            merchant_rating = float(candidate.facts.get("merchant_rating") or 0.0) / 5.0
            business_boost = 1.0 if candidate.facts.get("is_recommended") else 0.0
            user_preference_match = float(candidate.facts.get("user_preference_match") or 0.0)
            candidate.final_score = (
                0.45 * max(candidate.dense_score, candidate.final_score)
                + 0.10 * candidate.dense_score
                + 0.10 * candidate.lexical_score
                + 0.10 * candidate.constraint_match
                + 0.05 * merchant_rating
                + 0.05 * user_preference_match
                + 0.05 * business_boost
            )
        return sorted(candidates, key=lambda item: item.final_score, reverse=True)
