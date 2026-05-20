from service.agent_runtime.state import AgentPlan
from service.rag.models import RecallCandidate
from service.rag.retriever import AdvancedRagRetriever
from service.rag.tracing import PipelineTrace, RagEvalOptions, TraceItem


class StubRoute:
    def __init__(self, candidates: list[RecallCandidate]) -> None:
        self._candidates = candidates

    def recall(self, plan, limit):
        return self._candidates


def _make_candidates(n: int = 5) -> list[RecallCandidate]:
    return [
        RecallCandidate(
            stable_key=f"dish:{i}",
            source_type="dish",
            source_id=i,
            route="stub",
            rank=i,
            score=1.0 - i * 0.1,
            facts={
                "dish_id": i,
                "dish_name": f"菜品{i}",
                "merchant_id": 1,
                "merchant_name": "测试商家",
                "price": 30.0,
                "cuisine_type": "湘菜",
                "is_available": True,
            },
            citation=f"菜品{i}描述",
        )
        for i in range(1, n + 1)
    ]


def _make_retriever(n: int = 5) -> AdvancedRagRetriever:
    return AdvancedRagRetriever(recall_routes=[StubRoute(_make_candidates(n))])


def _make_plan(normalized_query: str = "湘菜推荐") -> AgentPlan:
    return AgentPlan(
        intent="recommendation",
        normalized_query=normalized_query,
        requires_rag=True,
        filters={"cuisine_types": ["湘菜"]},
    )


def test_trace_captures_all_stages() -> None:
    retriever = _make_retriever()
    trace = PipelineTrace()
    opts = RagEvalOptions()
    retriever.retrieve("推荐湘菜", _make_plan(), memories=[], limit=5, trace=trace, eval_options=opts)

    assert not trace.cache_hit
    assert len(trace.recall_per_route) > 0
    assert len(trace.after_fusion) > 0
    assert len(trace.after_hard_filter) > 0
    assert len(trace.after_diversify) > 0


def test_trace_records_latencies() -> None:
    retriever = _make_retriever()
    trace = PipelineTrace()
    opts = RagEvalOptions()
    retriever.retrieve("推荐湘菜", _make_plan(), memories=[], limit=5, trace=trace, eval_options=opts)

    assert trace.parallel_recall_total_ms >= 0
    assert trace.fusion_latency_ms >= 0
    assert trace.filter_latency_ms >= 0
    assert trace.diversify_latency_ms >= 0


def test_trace_items_have_keys_and_scores() -> None:
    retriever = _make_retriever()
    trace = PipelineTrace()
    opts = RagEvalOptions()
    retriever.retrieve("推荐湘菜", _make_plan(), memories=[], limit=5, trace=trace, eval_options=opts)

    for item in trace.after_fusion:
        assert item.key.startswith("dish:")
        assert isinstance(item, TraceItem)


def test_keys_at_helper() -> None:
    trace = PipelineTrace()
    trace.after_fusion = [TraceItem(key="a", score=1.0), TraceItem(key="b", score=0.5)]
    assert trace.keys_at("after_fusion") == ["a", "b"]


def test_skip_cross_encoder() -> None:
    retriever = _make_retriever()
    trace = PipelineTrace()
    opts = RagEvalOptions(skip_cross_encoder=True)
    retriever.retrieve("推荐湘菜", _make_plan(), memories=[], limit=5, trace=trace, eval_options=opts)

    assert trace.after_cross_encoder == []
    assert trace.cross_encoder_latency_ms == 0.0


def test_skip_weighted_rerank() -> None:
    retriever = _make_retriever()
    trace = PipelineTrace()
    opts = RagEvalOptions(skip_weighted_rerank=True)
    retriever.retrieve("推荐湘菜", _make_plan(), memories=[], limit=5, trace=trace, eval_options=opts)

    assert trace.after_weighted_rerank == []
    assert trace.weighted_rerank_latency_ms == 0.0
    assert len(trace.after_diversify) > 0


def test_disable_cache_bypasses_cache() -> None:
    retriever = _make_retriever()
    plan = _make_plan()

    retriever.retrieve("推荐湘菜", plan, memories=[], limit=5)

    trace = PipelineTrace()
    opts = RagEvalOptions(disable_cache=True)
    retriever.retrieve("推荐湘菜", plan, memories=[], limit=5, trace=trace, eval_options=opts)

    assert not trace.cache_hit
    assert len(trace.after_fusion) > 0
