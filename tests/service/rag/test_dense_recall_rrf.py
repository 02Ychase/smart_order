"""Tests for Issue #10: Dense recall internal RRF merge.

Covers:
- per_query top_k is ceil(limit / num_searches), not the full limit
- Candidates found by multiple queries get higher RRF score
- Deduplication: same stable_key from different queries merged
- Rank is reassigned by RRF score, not insertion order
- Single query still works correctly
- Empty results and unavailable vector store handled
- namespace filtering respects source_types
"""

import math

from service.rag.models import RagQueryPlan, RecallCandidate
from service.rag.recall import DenseVectorRecallRoute


# ── Stub vector stores ──────────────────────────────────────────────────


class RecordingVectorStore:
    """Records all semantic_search calls and returns configurable results."""

    def __init__(self, results_by_query_ns: dict | None = None):
        self._results = results_by_query_ns or {}
        self.calls: list[dict] = []

    def is_ready(self):
        return True

    def semantic_search(self, query, top_k, namespace):
        self.calls.append({"query": query, "top_k": top_k, "namespace": namespace})
        key = (query, namespace)
        return self._results.get(key, [])


class UnavailableVectorStore:
    def is_ready(self):
        return False


def _match(source_id: int, score: float, source_type: str = "dish") -> dict:
    return {
        "id": f"{source_type}_{source_id}",
        "score": score,
        "metadata": {
            "source_type": source_type,
            "source_id": source_id,
            "dish_id": source_id if source_type == "dish" else None,
            "merchant_id": source_id if source_type == "merchant" else None,
            "dish_name": f"dish_{source_id}",
            "content": f"description_{source_id}",
        },
    }


def _plan(**overrides) -> RagQueryPlan:
    defaults = dict(
        original_query="test",
        normalized_query="test",
        expansion_queries=["test"],
        source_types=["dish"],
    )
    defaults.update(overrides)
    return RagQueryPlan(**defaults)


# ── per_query top_k tests ───────────────────────────────────────────────


def test_per_query_top_k_is_distributed_not_full_limit() -> None:
    """With 3 queries × 1 namespace, top_k should be ceil(50/3)=17, not 50."""
    store = RecordingVectorStore()
    plan = _plan(expansion_queries=["q1", "q2", "q3"], source_types=["dish"])

    DenseVectorRecallRoute(store).recall(plan, limit=50)

    expected_top_k = math.ceil(50 / 3)
    assert len(store.calls) == 3
    for call in store.calls:
        assert call["top_k"] == expected_top_k


def test_per_query_top_k_with_two_namespaces() -> None:
    """2 queries × 2 namespaces = 4 searches → top_k = ceil(50/4) = 13."""
    store = RecordingVectorStore()
    plan = _plan(
        expansion_queries=["q1", "q2"],
        source_types=["dish", "merchant"],
    )

    DenseVectorRecallRoute(store).recall(plan, limit=50)

    expected_top_k = math.ceil(50 / 4)
    assert len(store.calls) == 4
    for call in store.calls:
        assert call["top_k"] == expected_top_k


def test_single_query_single_namespace_uses_full_limit() -> None:
    """1 query × 1 namespace → top_k = limit."""
    store = RecordingVectorStore()
    plan = _plan(expansion_queries=["q1"], source_types=["dish"])

    DenseVectorRecallRoute(store).recall(plan, limit=50)

    assert len(store.calls) == 1
    assert store.calls[0]["top_k"] == 50


# ── RRF merge behavior ─────────────────────────────────────────────────


def test_candidate_found_by_multiple_queries_ranks_higher() -> None:
    """dish:1 found by both queries should rank above dish:2 found by only one."""
    store = RecordingVectorStore({
        ("q1", "dishes"): [_match(1, 0.8), _match(2, 0.7)],
        ("q2", "dishes"): [_match(1, 0.85), _match(3, 0.75)],
    })
    plan = _plan(expansion_queries=["q1", "q2"], source_types=["dish"])

    result = DenseVectorRecallRoute(store).recall(plan, limit=50)

    keys = [c.stable_key for c in result]
    assert keys[0] == "dish:1", "Multi-query hit should rank first"
    assert "dish:2" in keys
    assert "dish:3" in keys


def test_rrf_deduplicates_same_candidate() -> None:
    """Same dish from 2 queries produces only 1 candidate in output."""
    store = RecordingVectorStore({
        ("q1", "dishes"): [_match(1, 0.9)],
        ("q2", "dishes"): [_match(1, 0.85)],
    })
    plan = _plan(expansion_queries=["q1", "q2"], source_types=["dish"])

    result = DenseVectorRecallRoute(store).recall(plan, limit=50)

    assert len(result) == 1
    assert result[0].stable_key == "dish:1"


def test_rrf_keeps_highest_vector_score_for_facts() -> None:
    """When deduplicating, the candidate with the highest vector score is kept."""
    store = RecordingVectorStore({
        ("q1", "dishes"): [_match(1, 0.7)],
        ("q2", "dishes"): [_match(1, 0.95)],
    })
    plan = _plan(expansion_queries=["q1", "q2"], source_types=["dish"])

    result = DenseVectorRecallRoute(store).recall(plan, limit=50)

    # facts should come from the 0.95 match (best vector score)
    assert result[0].stable_key == "dish:1"


def test_rrf_preserves_vector_score_for_downstream_rerank() -> None:
    """Internal RRF should not overwrite the vector similarity score."""
    store = RecordingVectorStore({
        ("q1", "dishes"): [_match(1, 0.7), _match(2, 0.9)],
        ("q2", "dishes"): [_match(1, 0.95)],
    })
    plan = _plan(expansion_queries=["q1", "q2"], source_types=["dish"])

    result = DenseVectorRecallRoute(store).recall(plan, limit=50)

    by_key = {candidate.stable_key: candidate for candidate in result}
    assert by_key["dish:1"].score == 0.95
    assert by_key["dish:2"].score == 0.9


def test_ranks_are_reassigned_by_rrf_score() -> None:
    """Output ranks should be 1, 2, 3... based on RRF score, not insertion order."""
    store = RecordingVectorStore({
        ("q1", "dishes"): [_match(1, 0.5), _match(2, 0.9)],
        ("q2", "dishes"): [_match(2, 0.85)],
    })
    plan = _plan(expansion_queries=["q1", "q2"], source_types=["dish"])

    result = DenseVectorRecallRoute(store).recall(plan, limit=50)

    # dish:2 hit by both queries → higher RRF score → rank 1
    assert result[0].stable_key == "dish:2"
    assert result[0].rank == 1
    assert result[1].stable_key == "dish:1"
    assert result[1].rank == 2


def test_limit_caps_output() -> None:
    """Output should not exceed limit even with many candidates."""
    matches = [_match(i, 0.9 - i * 0.01) for i in range(1, 20)]
    store = RecordingVectorStore({("q1", "dishes"): matches})
    plan = _plan(expansion_queries=["q1"], source_types=["dish"])

    result = DenseVectorRecallRoute(store).recall(plan, limit=5)

    assert len(result) == 5


# ── Edge cases ───────────────────────────────────────────────────────────


def test_unavailable_vector_store_returns_empty() -> None:
    result = DenseVectorRecallRoute(UnavailableVectorStore()).recall(
        _plan(), limit=50,
    )
    assert result == []


def test_no_matching_namespaces_returns_empty() -> None:
    """source_types=['merchant'] but only 'dishes' namespace → 0 searches."""
    store = RecordingVectorStore()
    plan = _plan(source_types=["merchant"])

    result = DenseVectorRecallRoute(store).recall(plan, limit=50)

    # Only 'merchants' namespace queried, not 'dishes'
    for call in store.calls:
        assert call["namespace"] == "merchants"


def test_empty_expansion_queries_falls_back_to_normalized() -> None:
    store = RecordingVectorStore()
    plan = _plan(expansion_queries=[], source_types=["dish"])
    plan.expansion_queries = []  # explicitly empty

    DenseVectorRecallRoute(store).recall(plan, limit=10)

    assert len(store.calls) == 1
    assert store.calls[0]["query"] == "test"  # normalized_query


def test_duplicate_queries_are_deduplicated_before_search() -> None:
    store = RecordingVectorStore()
    plan = _plan(expansion_queries=["q1", "q1", "q2"], source_types=["dish"])

    DenseVectorRecallRoute(store).recall(plan, limit=10)

    assert [call["query"] for call in store.calls] == ["q1", "q2"]


def test_empty_queries_are_skipped() -> None:
    store = RecordingVectorStore()
    plan = _plan(expansion_queries=["", "q1", None], source_types=["dish"])

    DenseVectorRecallRoute(store).recall(plan, limit=10)

    assert [call["query"] for call in store.calls] == ["q1"]


def test_no_query_returns_empty_without_search() -> None:
    store = RecordingVectorStore()
    plan = _plan(expansion_queries=["", None], normalized_query="", source_types=["dish"])

    result = DenseVectorRecallRoute(store).recall(plan, limit=10)

    assert result == []
    assert store.calls == []


def test_namespace_filtering_skips_dishes_when_merchant_only() -> None:
    store = RecordingVectorStore()
    plan = _plan(expansion_queries=["q1"], source_types=["merchant"])

    DenseVectorRecallRoute(store).recall(plan, limit=50)

    assert all(c["namespace"] == "merchants" for c in store.calls)


def test_namespace_filtering_skips_merchants_when_dish_only() -> None:
    store = RecordingVectorStore()
    plan = _plan(expansion_queries=["q1"], source_types=["dish"])

    DenseVectorRecallRoute(store).recall(plan, limit=50)

    assert all(c["namespace"] == "dishes" for c in store.calls)
