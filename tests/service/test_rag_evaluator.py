from tools.evaluate_assistant_rag import evaluate_cases


class StubRetriever:
    def retrieve(self, query, limit=5):
        return [
            type("Evidence", (), {
                "source_type": "dish",
                "source_id": 11,
                "facts": {"price": 28.0, "allergens": [], "cuisine_type": "川味麻辣"},
            })()
        ]


def test_evaluate_cases_reports_recall_and_constraint_pass_rate() -> None:
    cases = [
        {
            "query": "推荐几种川菜，2个人吃，100元以内，不要花生",
            "expected_source_ids": [11],
            "constraints": {"budget_max": 100, "party_size": 2, "exclude_allergens": ["花生"]},
        }
    ]

    metrics = evaluate_cases(cases, retriever=StubRetriever())

    assert metrics["case_count"] == 1
    assert metrics["recall_metrics"]["recall_at_5"] == 1.0
    assert metrics["recall_metrics"]["constraint_pass_rate"] == 1.0


def test_main_uses_advanced_retriever_with_case_constraints(monkeypatch) -> None:
    import sys as _sys
    import types as _types
    import tools.evaluate_assistant_rag as evaluator

    calls = {}

    class Session:
        def close(self):
            calls["closed"] = True

    class AdvancedRetriever:
        def __init__(self, session):
            calls["session"] = session

        def retrieve(self, original_query, agent_plan, memories, limit):
            calls["query"] = original_query
            calls["agent_plan"] = agent_plan
            return [
                type(
                    "Evidence",
                    (),
                    {
                        "source_type": "dish",
                        "source_id": 11,
                        "facts": {"cuisine_type": "湘菜", "dish_name": "辣椒炒肉"},
                        "title": "辣椒炒肉",
                        "citation": "鲜辣下饭",
                        "why_matched": ["湘菜", "辣"],
                    },
                )()
            ]

    session = Session()
    import types as _types2
    from dataclasses import dataclass, field as _field

    _mock_db = _types2.ModuleType("api.db")
    _mock_db.SessionLocal = lambda: session
    monkeypatch.setitem(_sys.modules, "api.db", _mock_db)

    @dataclass
    class _MockAgentPlan:
        intent: str = "recommendation"
        normalized_query: str = ""
        requires_rag: bool = True
        filters: dict = _field(default_factory=dict)
        tool_calls: list = _field(default_factory=list)
        should_answer_directly: bool = True
        response_hint: str = ""

    _mock_state = _types2.ModuleType("service.agent_runtime.state")
    _mock_state.AgentPlan = _MockAgentPlan
    _mock_state.GraphToolCall = dataclass
    monkeypatch.setitem(_sys.modules, "service.agent_runtime.state", _mock_state)

    _mock_retriever_mod = _types2.ModuleType("service.rag.retriever")
    _mock_retriever_mod.AdvancedRagRetriever = AdvancedRetriever
    monkeypatch.setitem(_sys.modules, "service.rag.retriever", _mock_retriever_mod)
    monkeypatch.setattr(
        evaluator,
        "load_cases",
        lambda path: [
            {
                "query": "帮我推荐几个比较辣的湘菜",
                "expected_source_type": "dish",
                "constraints": {
                    "allowed_cuisine_types": ["湘菜"],
                    "required_keywords": ["辣"],
                },
            }
        ],
    )

    monkeypatch.setattr("sys.argv", ["evaluate_assistant_rag.py"])
    assert evaluator.main() == 0

    assert calls["session"] is session
    assert calls["closed"] is True
    assert calls["query"] == "帮我推荐几个比较辣的湘菜"
    assert calls["agent_plan"].filters["cuisine_types"] == ["湘菜"]
    assert calls["agent_plan"].filters["flavor_preferences"] == ["辣"]


def test_latency_tracker_percentiles() -> None:
    from tools.evaluate_assistant_rag import _LatencyTracker

    tracker = _LatencyTracker()
    for ms in [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]:
        tracker.record(ms)

    stats = tracker.stats()
    assert stats["count"] == 10
    assert stats["p50_ms"] > 0
    assert stats["p95_ms"] > stats["p50_ms"]
    assert stats["p99_ms"] >= stats["p95_ms"]
    assert stats["mean_ms"] == 55.0


def test_latency_tracker_empty() -> None:
    from tools.evaluate_assistant_rag import _LatencyTracker

    tracker = _LatencyTracker()
    stats = tracker.stats()
    assert stats["count"] == 0
    assert stats["mean_ms"] == 0


def test_evaluate_cases_tracks_latency_and_cache() -> None:
    from tools.evaluate_assistant_rag import evaluate_cases

    class LatencyTestRetriever:
        def __init__(self):
            self._cache = {}

        def retrieve(self, query, limit=5):
            return [
                type("Evidence", (), {
                    "source_type": "dish",
                    "source_id": 1,
                    "facts": {"cuisine_type": "湘菜"},
                    "title": "test",
                    "citation": "test citation",
                    "why_matched": [],
                })()
            ]

    cases = [{"query": "test", "expected_source_type": "dish", "constraints": {}}]
    metrics = evaluate_cases(cases, LatencyTestRetriever())

    assert "latency" in metrics
    assert metrics["latency"]["count"] == 1
    assert "cache" in metrics
    assert "hit_rate" in metrics["cache"]


def test_evaluate_cases_with_correlation_pairs(monkeypatch) -> None:
    from tools.evaluate_assistant_rag import evaluate_cases, _LatencyTracker

    class CorrelationRetriever:
        def __init__(self):
            self._cache = {}

        def retrieve(self, query, limit=5):
            return [
                type("Evidence", (), {
                    "source_type": "dish",
                    "source_id": 1,
                    "facts": {"cuisine_type": "湘菜", "dish_name": "辣椒炒肉"},
                    "title": "辣椒炒肉",
                    "citation": "鲜辣",
                    "why_matched": ["湘菜"],
                })()
            ]

    def fake_llm_score(query, evidence, model_name=None):
        return 4

    monkeypatch.setattr(
        "tools.evaluate_assistant_rag._llm_relevance_score",
        fake_llm_score,
    )

    cases = [{
        "query": "湘菜推荐",
        "expected_source_type": "dish",
        "constraints": {},
        "relevance_grades": {"dish:1": 5},
    }]
    metrics = evaluate_cases(cases, CorrelationRetriever(), enable_llm_judge=True)

    assert "llm_judge" in metrics
    assert metrics["llm_judge"]["mean_score"] == 4.0
    assert metrics["llm_judge"]["human_correlation"] is None


def test_evaluate_cases_without_llm_judge_skips_llm_calls() -> None:
    from tools.evaluate_assistant_rag import evaluate_cases

    class NoLLMRetriever:
        def __init__(self):
            self._cache = {}

        def retrieve(self, query, limit=5):
            return [
                type("Evidence", (), {
                    "source_type": "dish",
                    "source_id": 1,
                    "facts": {},
                    "title": "test",
                    "citation": "",
                    "why_matched": [],
                })()
            ]

    cases = [{"query": "test", "constraints": {}}]
    metrics = evaluate_cases(cases, NoLLMRetriever(), enable_llm_judge=False)
    assert "llm_judge" not in metrics


def test_ablation_summary_empty() -> None:
    from tools.evaluate_assistant_rag import _summarize_ablation

    summary = _summarize_ablation([])
    assert isinstance(summary, dict)
    assert len(summary) == 0
