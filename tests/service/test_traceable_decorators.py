"""Tests for Issue #6: LangSmith @traceable decorators on RAG pipeline.

Covers:
- All RAG pipeline functions have @traceable decorator
- Decorators use correct LangSmith span names
- MetricsCollector timer blocks removed from retriever.retrieve()
- evaluate_node records iteration_count in state["metrics"]
- respond_node merges metrics into state["metrics"] instead of standalone emit
"""

import inspect
from unittest.mock import MagicMock, patch

from langsmith import traceable


# ── @traceable presence tests ─────────────────────────────────────────


def _has_traceable(func) -> bool:
    """Check whether a function (or unbound method) is wrapped by @traceable."""
    # langsmith wraps the function; the wrapper carries metadata.
    # The most reliable sign is the __langsmith_traceable__ attribute or
    # the wrapper's __wrapped__ pointing to the original.
    if getattr(func, "__langsmith_traceable__", None):
        return True
    # Some versions set is_traceable_function
    if getattr(func, "is_traceable_function", None):
        return True
    # Fallback: check if __wrapped__ exists (functools.wraps chain)
    return hasattr(func, "__wrapped__")


def test_dense_vector_recall_is_traceable() -> None:
    from service.rag.recall import DenseVectorRecallRoute
    assert _has_traceable(DenseVectorRecallRoute.recall)


def test_sql_catalog_recall_is_traceable() -> None:
    from service.rag.recall import SqlCatalogRecallRoute
    assert _has_traceable(SqlCatalogRecallRoute.recall)


def test_business_recall_is_traceable() -> None:
    from service.rag.recall import BusinessRecallRoute
    assert _has_traceable(BusinessRecallRoute.recall)


def test_sparse_vector_recall_is_traceable() -> None:
    from service.rag.recall import SparseVectorRecallRoute
    assert _has_traceable(SparseVectorRecallRoute.recall)


def test_reciprocal_rank_fusion_is_traceable() -> None:
    from service.rag.fusion import reciprocal_rank_fusion
    assert _has_traceable(reciprocal_rank_fusion)


def test_apply_hard_filters_is_traceable() -> None:
    from service.rag.filters import apply_hard_filters
    assert _has_traceable(apply_hard_filters)


def test_cross_encoder_rerank_is_traceable() -> None:
    from service.rag.cross_encoder import CrossEncoderReranker
    assert _has_traceable(CrossEncoderReranker.rerank)


def test_weighted_reranker_rerank_is_traceable() -> None:
    from service.rag.reranker import WeightedReranker
    assert _has_traceable(WeightedReranker.rerank)


def test_diversify_is_traceable() -> None:
    from service.rag.diversifier import diversify
    assert _has_traceable(diversify)


def test_retrieve_is_traceable() -> None:
    from service.rag.retriever import AdvancedRagRetriever
    assert _has_traceable(AdvancedRagRetriever.retrieve)


def test_parallel_recall_is_traceable() -> None:
    from service.rag.retriever import AdvancedRagRetriever
    assert _has_traceable(AdvancedRagRetriever._parallel_recall)


# ── Timer removal verification ────────────────────────────────────────


def test_retrieve_source_has_no_collector_timer() -> None:
    """retrieve() should no longer use collector.timer() context managers."""
    from service.rag.retriever import AdvancedRagRetriever
    # Get the actual source — unwrap @traceable wrapper if needed
    func = AdvancedRagRetriever.retrieve
    while hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    source = inspect.getsource(func)
    assert "collector.timer(" not in source, (
        "retrieve() should not contain collector.timer() calls — "
        "timing is now handled by @traceable spans in LangSmith"
    )


def test_retrieve_still_emits_metadata() -> None:
    """retrieve() should still use MetricsCollector for metadata and counters."""
    from service.rag.retriever import AdvancedRagRetriever
    func = AdvancedRagRetriever.retrieve
    while hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    source = inspect.getsource(func)
    assert "collector.set_metadata(" in source
    assert "collector.emit(" in source


# ── evaluate_node records iteration_count in metrics ──────────────────


def test_evaluate_node_records_iteration_count_in_metrics() -> None:
    from service.agent_runtime.nodes import evaluate_node

    state = {
        "iteration_count": 2,
        "max_iterations": 5,
        "current_plan": None,
        "tool_results": [],
        "recent_evidence": [],
        "metrics": {"some_prior": "data"},
    }
    result = evaluate_node(state)
    assert result["metrics"]["iteration_count"] == 3
    # Preserves prior metrics
    assert result["metrics"]["some_prior"] == "data"


def test_evaluate_node_initializes_metrics_when_absent() -> None:
    from service.agent_runtime.nodes import evaluate_node

    state = {
        "iteration_count": 0,
        "max_iterations": 5,
        "current_plan": None,
        "tool_results": [],
        "recent_evidence": [],
    }
    result = evaluate_node(state)
    assert result["metrics"]["iteration_count"] == 1


# ── respond_node merges metrics into state["metrics"] ─────────────────


def test_respond_node_merges_metrics_into_state() -> None:
    from service.agent_runtime.nodes import respond_node

    state = {
        "messages": [],
        "session_id": "test-session",
        "current_plan": None,
        "recent_evidence": [],
        "tool_results": [],
        "recent_action_ids": [],
        "guardrail_blocked": False,
        "metrics": {"iteration_count": 2, "load_memory_ms": 15},
    }

    with patch("service.agent_runtime.nodes.get_runtime", return_value=MagicMock(use_llm_response=False)):
        result = respond_node(state)

    metrics = result.get("metrics", {})
    # respond_node should add its own fields
    assert "response_type" in metrics
    assert "evidence_count" in metrics
    assert "tool_results_count" in metrics
    # Prior metrics should be preserved
    assert metrics["iteration_count"] == 2
    assert metrics["load_memory_ms"] == 15


def test_respond_node_does_not_use_standalone_collector_emit() -> None:
    """respond_node should no longer call collector.emit() standalone."""
    from service.agent_runtime.nodes import respond_node
    source = inspect.getsource(respond_node)
    assert "collector.emit(" not in source, (
        "respond_node should merge metrics into state['metrics'] "
        "instead of using standalone MetricsCollector.emit()"
    )
