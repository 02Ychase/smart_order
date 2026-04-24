from __future__ import annotations

from service.agent_state import EvidencePack


class RagReranker:
    def rerank(self, candidates: list[EvidencePack], limit: int = 5) -> list[EvidencePack]:
        for candidate in candidates:
            facts = candidate.facts
            semantic_score = float(facts.get("semantic_score", 0.0))
            keyword_score = float(facts.get("keyword_score", 0.0))
            merchant_rating = float(facts.get("merchant_rating", 0.0)) / 5.0
            recommendation_boost = 1.0 if facts.get("is_recommended") else 0.0
            constraint_match_score = float(facts.get("constraint_match_score", 0.0))
            candidate.score = (
                0.45 * semantic_score
                + 0.20 * keyword_score
                + 0.15 * merchant_rating
                + 0.10 * recommendation_boost
                + 0.10 * constraint_match_score
            )
        return sorted(candidates, key=lambda item: item.score, reverse=True)[:limit]
