"""Tests for Issue #4: RAG dynamic output limit.

Covers:
- _output_limit: no user limit → default; user limit ≤ max → honoured; user limit > max → capped
- _output_limit: edge cases (0, negative, non-integer)
- retrieve() signature: max_limit flows through to _output_limit
- Cache key includes effective output_limit, so different limits don't share cache
- rag_node reads limit from config instead of hardcoded 3
"""

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

from service.config import AppConfig, set_config
from service.rag.retriever import AdvancedRagRetriever


# ── Helpers ──────────────────────────────────────────────────────────


@dataclass
class FakePlan:
    """Minimal stand-in for RagQueryPlan with the fields _output_limit needs."""
    should_filters: dict[str, Any] = field(default_factory=dict)
    must_filters: dict[str, Any] = field(default_factory=dict)
    normalized_query: str = "test"
    original_query: str = "test"
    expansion_queries: list[str] = field(default_factory=list)
    source_types: list[str] = field(default_factory=lambda: ["dish"])
    answer_mode: str = "recommendation"
    preferred_dishes: list[str] = field(default_factory=list)
    preferred_merchants: list[str] = field(default_factory=list)


# ── _output_limit unit tests ────────────────────────────────────────


def test_output_limit_no_user_limit_returns_default() -> None:
    plan = FakePlan(should_filters={})
    assert AdvancedRagRetriever._output_limit(plan, default=5, max_limit=20) == 5


def test_output_limit_user_limit_within_max_honoured() -> None:
    plan = FakePlan(should_filters={"limit": 8})
    assert AdvancedRagRetriever._output_limit(plan, default=5, max_limit=20) == 8


def test_output_limit_user_limit_exceeds_max_capped() -> None:
    plan = FakePlan(should_filters={"limit": 50})
    assert AdvancedRagRetriever._output_limit(plan, default=5, max_limit=20) == 20


def test_output_limit_user_limit_zero_returns_floor() -> None:
    plan = FakePlan(should_filters={"limit": 0})
    assert AdvancedRagRetriever._output_limit(plan, default=5, max_limit=20) == 3


def test_output_limit_user_limit_negative_returns_floor() -> None:
    plan = FakePlan(should_filters={"limit": -3})
    assert AdvancedRagRetriever._output_limit(plan, default=5, max_limit=20) == 3


def test_output_limit_user_limit_one_returns_floor() -> None:
    """Even when user says 'one', RAG returns at least RAG_EVIDENCE_FLOOR candidates."""
    plan = FakePlan(should_filters={"limit": 1})
    assert AdvancedRagRetriever._output_limit(plan, default=5, max_limit=20) == 3


def test_output_limit_user_limit_non_integer_returns_default() -> None:
    plan = FakePlan(should_filters={"limit": "abc"})
    assert AdvancedRagRetriever._output_limit(plan, default=5, max_limit=20) == 5


def test_output_limit_user_limit_none_returns_default() -> None:
    plan = FakePlan(should_filters={"limit": None})
    assert AdvancedRagRetriever._output_limit(plan, default=5, max_limit=20) == 5


def test_output_limit_string_number_parsed() -> None:
    """Planner may produce limit as string '10' from JSON."""
    plan = FakePlan(should_filters={"limit": "10"})
    assert AdvancedRagRetriever._output_limit(plan, default=5, max_limit=20) == 10


# ── Cache key includes effective output_limit ────────────────────────


def test_cache_key_differs_by_output_limit() -> None:
    """Same query, different effective output_limit → different cache keys."""
    retriever = AdvancedRagRetriever(recall_routes=[])
    plan = FakePlan(normalized_query="推荐川菜", original_query="推荐川菜")

    key_a = retriever._cache_key(plan, memories=None, output_limit=3)
    key_b = retriever._cache_key(plan, memories=None, output_limit=5)
    key_c = retriever._cache_key(plan, memories=None, output_limit=5)

    assert key_a != key_b, "Different output limits should produce different cache keys"
    assert key_b == key_c, "Same output limit should produce same cache key"


# ── retrieve() max_limit parameter ──────────────────────────────────


def test_retrieve_respects_max_limit_from_config() -> None:
    """When max_limit is not passed, retrieve() reads from config."""
    cfg = AppConfig()
    cfg.rag.output_limit_max = 15
    set_config(cfg)

    plan = FakePlan(should_filters={"limit": 30})

    retriever = AdvancedRagRetriever(recall_routes=[])
    # _output_limit should use config's max (15), not the hardcoded default (20)
    result = retriever._output_limit(plan, default=5, max_limit=cfg.rag.output_limit_max)
    assert result == 15

    # Restore default config
    set_config(AppConfig())


def test_retrieve_explicit_max_limit_overrides_config() -> None:
    """When caller passes max_limit explicitly, it takes precedence over config."""
    cfg = AppConfig()
    cfg.rag.output_limit_max = 15
    set_config(cfg)

    plan = FakePlan(should_filters={"limit": 12})

    # Explicit max_limit=10 should override config's 15
    result = AdvancedRagRetriever._output_limit(plan, default=5, max_limit=10)
    assert result == 10

    # Restore default config
    set_config(AppConfig())


# ── rag_node uses config instead of hardcoded 3 ─────────────────────


def test_rag_node_passes_config_limits() -> None:
    """rag_node should pass output_limit_default and output_limit_max from config."""
    from service.agent_runtime.state import AgentPlan

    cfg = AppConfig()
    cfg.rag.output_limit_default = 7
    cfg.rag.output_limit_max = 15
    set_config(cfg)

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = []

    plan = AgentPlan(intent="recommendation", requires_rag=True)

    with patch("service.agent_runtime.nodes.get_runtime") as mock_get_runtime:
        runtime = MagicMock()
        runtime.retriever = mock_retriever
        mock_get_runtime.return_value = runtime

        from service.agent_runtime.nodes import rag_node
        from langchain_core.messages import HumanMessage

        state = {
            "messages": [HumanMessage(content="推荐几个菜")],
            "current_plan": plan,
            "loaded_user_memories": [],
            "tool_results": [],
        }

        rag_node(state, config={"configurable": {"runtime": runtime}})

        call_kwargs = mock_retriever.retrieve.call_args
        assert call_kwargs.kwargs["limit"] == 7
        assert call_kwargs.kwargs["max_limit"] == 15

    # Restore default config
    set_config(AppConfig())
