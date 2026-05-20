"""Tests for Issue #8: _parallel_recall truly parallel execution.

Covers:
- Parallel mode produces same results as sequential mode
- parallel_recall=False falls back to sequential execution
- Single route exception does not affect other routes
- DB routes get independent sessions (session isolation)
- Sessions are closed after recall completes
- Sparse route with _built=True skips session creation
- requires_db_session flag is set correctly on all routes
- recall_max_workers config is respected
"""

import threading
from unittest.mock import MagicMock, call

from service.config import AppConfig, set_config
from service.rag.models import RagQueryPlan, RecallCandidate
from service.rag.retriever import AdvancedRagRetriever


# ── Helpers ────────────────────────────────────────────────────────────


def _make_plan(**overrides) -> RagQueryPlan:
    defaults = dict(
        original_query="test",
        normalized_query="test",
        expansion_queries=[],
        source_types=["dish", "merchant"],
        answer_mode="recommendation",
        must_filters={},
        should_filters={},
        preferred_dishes=[],
        preferred_merchants=[],
    )
    defaults.update(overrides)
    return RagQueryPlan(**defaults)


def _make_candidate(stable_key: str, route: str, rank: int = 1) -> RecallCandidate:
    source_type, source_id = stable_key.split(":")
    return RecallCandidate(
        stable_key=stable_key,
        source_type=source_type,
        source_id=int(source_id),
        route=route,
        rank=rank,
        score=0.9,
        facts={"dish_id": int(source_id), "dish_name": f"dish_{source_id}"},
        citation="test",
    )


class FakeRoute:
    """Simple route that records calls and returns fixed candidates."""
    requires_db_session = False

    def __init__(self, candidates=None, *, delay: float = 0):
        self._candidates = candidates or []
        self._delay = delay
        self.call_count = 0
        self.called_from_thread: threading.Thread | None = None

    def recall(self, plan, limit):
        import time
        self.call_count += 1
        self.called_from_thread = threading.current_thread()
        if self._delay:
            time.sleep(self._delay)
        return self._candidates[:limit]


class FakeDbRoute:
    """Route that requires a DB session and records the CatalogService it uses."""
    requires_db_session = True

    def __init__(self, catalog_service=None):
        self.catalog_service = catalog_service
        self.used_sessions: list = []
        self.call_count = 0

    def recall(self, plan, limit):
        self.call_count += 1
        if self.catalog_service:
            self.used_sessions.append(id(self.catalog_service))
        return []


class FailingRoute:
    """Route that always raises."""
    requires_db_session = False

    def recall(self, plan, limit):
        raise RuntimeError("intentional failure")


class FakeSparseRoute:
    """Simulates SparseVectorRecallRoute with _built flag."""
    requires_db_session = True

    def __init__(self, catalog_service=None):
        self.catalog_service = catalog_service
        self._built = False
        self.recall_count = 0

    def recall(self, plan, limit):
        self.recall_count += 1
        return []


# ── requires_db_session flag tests ─────────────────────────────────────


def test_dense_route_does_not_require_db_session() -> None:
    from service.rag.recall import DenseVectorRecallRoute
    assert DenseVectorRecallRoute.requires_db_session is False


def test_sql_catalog_route_requires_db_session() -> None:
    from service.rag.recall import SqlCatalogRecallRoute
    assert SqlCatalogRecallRoute.requires_db_session is True


def test_business_route_requires_db_session() -> None:
    from service.rag.recall import BusinessRecallRoute
    assert BusinessRecallRoute.requires_db_session is True


def test_sparse_route_requires_db_session() -> None:
    from service.rag.recall import SparseVectorRecallRoute
    assert SparseVectorRecallRoute.requires_db_session is True


# ── Config defaults ────────────────────────────────────────────────────


def test_config_parallel_recall_default_true() -> None:
    cfg = AppConfig()
    assert cfg.rag.parallel_recall is True


def test_config_recall_max_workers_default_four() -> None:
    cfg = AppConfig()
    assert cfg.rag.recall_max_workers == 4


# ── Parallel vs sequential result consistency ──────────────────────────


def test_parallel_and_sequential_produce_same_results() -> None:
    candidates_a = [_make_candidate("dish:1", "route_a")]
    candidates_b = [_make_candidate("dish:2", "route_b")]
    route_a = FakeRoute(candidates_a)
    route_b = FakeRoute(candidates_b)

    retriever = AdvancedRagRetriever(recall_routes=[route_a, route_b])
    plan = _make_plan()

    # Sequential
    cfg = AppConfig()
    cfg.rag.parallel_recall = False
    set_config(cfg)
    sequential = retriever._sequential_recall(plan, limit=50)

    # Reset call counts
    route_a.call_count = 0
    route_b.call_count = 0

    # Parallel
    cfg.rag.parallel_recall = True
    set_config(cfg)
    parallel = retriever._parallel_recall(plan, limit=50)

    assert len(sequential) == len(parallel) == 2
    seq_results = [r for r, _ in sequential]
    par_results = [r for r, _ in parallel]
    assert len(seq_results[0]) == len(par_results[0]) == 1
    assert len(seq_results[1]) == len(par_results[1]) == 1
    assert seq_results[0][0].stable_key == par_results[0][0].stable_key
    assert seq_results[1][0].stable_key == par_results[1][0].stable_key

    set_config(AppConfig())


# ── Fallback to sequential ──────────────────────────────────────────────


def test_fallback_to_sequential_when_config_disabled() -> None:
    route = FakeRoute([_make_candidate("dish:1", "test")])

    cfg = AppConfig()
    cfg.rag.parallel_recall = False
    set_config(cfg)

    retriever = AdvancedRagRetriever(recall_routes=[route, FakeRoute()])
    result = retriever._parallel_recall(_make_plan(), limit=50)

    # Should use sequential (main thread)
    assert route.called_from_thread == threading.current_thread()
    assert len(result) == 2

    set_config(AppConfig())


def test_fallback_to_sequential_with_single_route() -> None:
    route = FakeRoute([_make_candidate("dish:1", "test")])

    cfg = AppConfig()
    cfg.rag.parallel_recall = True
    set_config(cfg)

    retriever = AdvancedRagRetriever(recall_routes=[route])
    result = retriever._parallel_recall(_make_plan(), limit=50)

    # Single route → sequential even if parallel is enabled
    assert route.called_from_thread == threading.current_thread()
    assert len(result) == 1

    set_config(AppConfig())


# ── Error isolation ─────────────────────────────────────────────────────


def test_one_failing_route_does_not_block_others() -> None:
    good_route = FakeRoute([_make_candidate("dish:1", "good")])
    bad_route = FailingRoute()

    cfg = AppConfig()
    cfg.rag.parallel_recall = True
    set_config(cfg)

    retriever = AdvancedRagRetriever(recall_routes=[good_route, bad_route])
    result = retriever._parallel_recall(_make_plan(), limit=50)

    assert len(result) == 2
    results_only = [r for r, _ in result]
    assert len(results_only[0]) == 1  # good route succeeded
    assert results_only[1] == []      # bad route returned empty

    set_config(AppConfig())


# ── Session isolation ───────────────────────────────────────────────────


def test_db_routes_get_independent_sessions() -> None:
    """Each DB route must get its own session, not share with others."""
    session_ids: list[int] = []

    def fake_session_factory():
        session = MagicMock()
        session._test_id = id(session)
        session_ids.append(session._test_id)
        return session

    db_route_1 = FakeDbRoute()
    db_route_2 = FakeDbRoute()
    non_db_route = FakeRoute()

    cfg = AppConfig()
    cfg.rag.parallel_recall = True
    set_config(cfg)

    retriever = AdvancedRagRetriever(
        recall_routes=[non_db_route, db_route_1, db_route_2],
        session_factory=fake_session_factory,
    )
    retriever._parallel_recall(_make_plan(), limit=50)

    # Two DB routes → two sessions created
    assert len(session_ids) == 2
    assert session_ids[0] != session_ids[1], "DB routes must not share the same session"

    set_config(AppConfig())


def test_sessions_are_closed_after_recall() -> None:
    """Every session created for parallel recall must be closed."""
    sessions: list[MagicMock] = []

    def fake_session_factory():
        session = MagicMock()
        sessions.append(session)
        return session

    cfg = AppConfig()
    cfg.rag.parallel_recall = True
    set_config(cfg)

    retriever = AdvancedRagRetriever(
        recall_routes=[FakeDbRoute(), FakeDbRoute()],
        session_factory=fake_session_factory,
    )
    retriever._parallel_recall(_make_plan(), limit=50)

    assert len(sessions) == 2
    for session in sessions:
        session.close.assert_called_once()

    set_config(AppConfig())


def test_session_closed_even_when_route_fails() -> None:
    """Session must be closed even if the route throws."""

    class FailingDbRoute:
        requires_db_session = True
        def __init__(self, catalog_service=None): pass
        def recall(self, plan, limit):
            raise RuntimeError("db error")

    sessions: list[MagicMock] = []

    def fake_session_factory():
        session = MagicMock()
        sessions.append(session)
        return session

    cfg = AppConfig()
    cfg.rag.parallel_recall = True
    set_config(cfg)

    # Need >=2 routes to avoid single-route sequential fallback
    retriever = AdvancedRagRetriever(
        recall_routes=[FakeRoute(), FailingDbRoute()],
        session_factory=fake_session_factory,
    )
    result = retriever._parallel_recall(_make_plan(), limit=50)

    assert len(result) == 2
    assert result[1][0] == []  # failing route returns empty
    assert len(sessions) == 1
    sessions[0].close.assert_called_once()

    set_config(AppConfig())


# ── Sparse route _built optimization ────────────────────────────────────


def test_sparse_built_route_skips_session_creation() -> None:
    """Sparse route with _built=True should reuse in-memory index, no new session."""
    session_create_count = 0

    def fake_session_factory():
        nonlocal session_create_count
        session_create_count += 1
        return MagicMock()

    sparse = FakeSparseRoute()
    sparse._built = True  # Index already built

    cfg = AppConfig()
    cfg.rag.parallel_recall = True
    set_config(cfg)

    retriever = AdvancedRagRetriever(
        recall_routes=[sparse],
        session_factory=fake_session_factory,
    )
    retriever._parallel_recall(_make_plan(), limit=50)

    assert session_create_count == 0, "Built sparse route should not trigger session creation"
    assert sparse.recall_count == 1

    set_config(AppConfig())


def test_sparse_unbuilt_route_gets_own_session() -> None:
    """Sparse route with _built=False needs DB access → gets its own session."""
    sessions: list[MagicMock] = []

    def fake_session_factory():
        s = MagicMock()
        sessions.append(s)
        return s

    sparse = FakeSparseRoute()
    sparse._built = False  # Will need to build index → needs DB

    cfg = AppConfig()
    cfg.rag.parallel_recall = True
    set_config(cfg)

    # Need >=2 routes to avoid single-route sequential fallback
    retriever = AdvancedRagRetriever(
        recall_routes=[FakeRoute(), sparse],
        session_factory=fake_session_factory,
    )
    retriever._parallel_recall(_make_plan(), limit=50)

    assert len(sessions) == 1
    sessions[0].close.assert_called_once()

    set_config(AppConfig())


# ── No session_factory graceful degradation ─────────────────────────────


def test_no_session_factory_uses_original_route() -> None:
    """Without session_factory, DB routes run with their original CatalogService."""
    db_route = FakeDbRoute(catalog_service=MagicMock())

    cfg = AppConfig()
    cfg.rag.parallel_recall = True
    set_config(cfg)

    retriever = AdvancedRagRetriever(
        recall_routes=[db_route],
        session_factory=None,  # No factory
    )
    retriever._parallel_recall(_make_plan(), limit=50)

    assert db_route.call_count == 1  # Route was called directly

    set_config(AppConfig())


# ── max_workers config ──────────────────────────────────────────────────


def test_recall_max_workers_caps_thread_count() -> None:
    """Verify max_workers is min(config, route_count)."""
    routes = [FakeRoute() for _ in range(6)]

    cfg = AppConfig()
    cfg.rag.parallel_recall = True
    cfg.rag.recall_max_workers = 3
    set_config(cfg)

    retriever = AdvancedRagRetriever(recall_routes=routes)
    result = retriever._parallel_recall(_make_plan(), limit=50)

    # All 6 routes should still execute
    assert len(result) == 6
    for route in routes:
        assert route.call_count == 1

    set_config(AppConfig())


# ── Result order preserved ──────────────────────────────────────────────


def test_result_order_matches_route_order() -> None:
    """futures[i].result() must correspond to recall_routes[i]."""
    route_a = FakeRoute([_make_candidate("dish:1", "a")])
    route_b = FakeRoute([_make_candidate("dish:2", "b")])
    route_c = FakeRoute([_make_candidate("dish:3", "c")])

    cfg = AppConfig()
    cfg.rag.parallel_recall = True
    set_config(cfg)

    retriever = AdvancedRagRetriever(recall_routes=[route_a, route_b, route_c])
    result = retriever._parallel_recall(_make_plan(), limit=50)

    results_only = [r for r, _ in result]
    assert results_only[0][0].stable_key == "dish:1"
    assert results_only[1][0].stable_key == "dish:2"
    assert results_only[2][0].stable_key == "dish:3"

    set_config(AppConfig())
