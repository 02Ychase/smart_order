from __future__ import annotations

from langsmith import traceable

from service.rag.models import FusedCandidate, RecallCandidate


@traceable(name="reciprocal_rank_fusion")
def reciprocal_rank_fusion(route_results: list[list[RecallCandidate]], limit: int = 50, k: int = 60) -> list[FusedCandidate]:
    by_key: dict[str, FusedCandidate] = {}
    totals: dict[str, float] = {}
    best_by_route_key: dict[tuple[str, str], RecallCandidate] = {}

    for candidates in route_results:
        for candidate in candidates:
            route_key = (candidate.route, candidate.stable_key)
            current = best_by_route_key.get(route_key)
            if current is None or candidate.rank < current.rank or (
                candidate.rank == current.rank and candidate.score > current.score
            ):
                best_by_route_key[route_key] = candidate

    for candidate in best_by_route_key.values():
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
        else:
            _merge_facts(fused, candidate)
            if not fused.citation and candidate.citation:
                fused.citation = candidate.citation
        fused.route_scores[candidate.route] = candidate.score
        fused.route_ranks[candidate.route] = candidate.rank
        if candidate.route == "dense":
            fused.dense_score = max(fused.dense_score, candidate.score)
        if candidate.route in {"sparse", "sql"}:
            fused.lexical_score = max(fused.lexical_score, candidate.score)
        # 对同一个候选，把它在每一路召回中的“排名贡献”累加起来；一路里排名越靠前贡献越大，被多路召回同时命中 贡献会叠加。
        totals[candidate.stable_key] = totals.get(candidate.stable_key, 0.0) + 1.0 / (k + candidate.rank)

    fused_items = list(by_key.values())
    for item in fused_items:
        item.final_score = totals[item.stable_key]
    return sorted(fused_items, key=lambda item: item.final_score, reverse=True)[:limit]


def _merge_facts(fused: FusedCandidate, candidate: RecallCandidate) -> None:
    for key, value in candidate.facts.items():
        current = fused.facts.get(key)
        if key not in fused.facts or (_has_value(value) and not _has_value(current)):
            fused.facts[key] = value


def _has_value(value) -> bool:
    return value is not None and value != "" and value != []
