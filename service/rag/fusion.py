from __future__ import annotations

from service.rag.models import FusedCandidate, RecallCandidate


def reciprocal_rank_fusion(route_results: list[list[RecallCandidate]], limit: int = 50, k: int = 60) -> list[FusedCandidate]:
    by_key: dict[str, FusedCandidate] = {}
    totals: dict[str, float] = {}

    for candidates in route_results:
        for candidate in candidates:
            fused = by_key.get(candidate.stable_key)
            if fused is None:
                fused = FusedCandidate(
                    stable_key=candidate.stable_key,
                    source_type=candidate.source_type,
                    source_id=candidate.source_id,
                    facts=dict(candidate.facts),
                    citation=candidate.citation,
                )
                by_key[candidate.stable_key] = fused
            fused.route_scores[candidate.route] = candidate.score
            fused.route_ranks[candidate.route] = candidate.rank
            if candidate.route == "dense":
                fused.dense_score = max(fused.dense_score, candidate.score)
            if candidate.route in {"sparse", "sql"}:
                fused.lexical_score = max(fused.lexical_score, candidate.score)
            totals[candidate.stable_key] = totals.get(candidate.stable_key, 0.0) + 1.0 / (k + candidate.rank)

    fused_items = list(by_key.values())
    for item in fused_items:
        item.final_score = totals[item.stable_key]
    return sorted(fused_items, key=lambda item: item.final_score, reverse=True)[:limit]
