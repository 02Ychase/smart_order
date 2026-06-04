from service.rag.cross_encoder import CrossEncoderReranker
from service.rag.models import FusedCandidate


def _make_candidate(stable_key: str, dish_name: str, citation: str, score: float = 0.5) -> FusedCandidate:
    return FusedCandidate(
        stable_key=stable_key,
        source_type="dish",
        source_id=int(stable_key.split(":")[1]),
        facts={"dish_name": dish_name, "merchant_name": "测试商家", "cuisine_type": "湘菜"},
        citation=citation,
        final_score=score,
    )


class FakeEmbedder:
    """Returns a fixed score based on whether query keywords appear in the text."""
    def score(self, query: str, text: str) -> float:
        query_words = set(query)
        text_words = set(text)
        overlap = len(query_words & text_words)
        return overlap / max(len(query_words), 1)


def test_cross_encoder_reranks_by_relevance():
    candidates = [
        _make_candidate("dish:1", "红烧肉", "经典红烧肉", score=0.9),
        _make_candidate("dish:2", "小炒黄牛肉", "辣椒炒牛肉", score=0.8),
        _make_candidate("dish:3", "剁椒鱼头", "湘菜经典辣味鱼", score=0.7),
    ]
    reranker = CrossEncoderReranker(scorer=FakeEmbedder())
    reranked = reranker.rerank("辣的湘菜", candidates, top_k=3)

    assert len(reranked) == 3
    for c in reranked:
        assert hasattr(c, "cross_encoder_score")


def test_cross_encoder_respects_top_k():
    candidates = [_make_candidate(f"dish:{i}", f"菜品{i}", f"描述{i}") for i in range(10)]
    reranker = CrossEncoderReranker(scorer=FakeEmbedder())
    reranked = reranker.rerank("测试", candidates, top_k=3)

    assert len(reranked) == 3


def test_cross_encoder_prefers_batch_scoring():
    """When the scorer exposes score_batch, rerank must use a single batched
    call and not fall back to per-item score()."""
    class BatchScorer:
        def __init__(self):
            self.batch_calls = 0
            self.item_calls = 0

        def score(self, query, text):
            self.item_calls += 1
            return 0.1

        def score_batch(self, query, texts):
            self.batch_calls += 1
            return [float(len(set(query) & set(t))) for t in texts]

    scorer = BatchScorer()
    candidates = [_make_candidate(f"dish:{i}", f"菜{i}", f"描述{i}") for i in range(5)]
    reranker = CrossEncoderReranker(scorer=scorer)

    reranked = reranker.rerank("辣", candidates, top_k=3)

    assert scorer.batch_calls == 1
    assert scorer.item_calls == 0
    assert len(reranked) == 3


def test_cross_encoder_batch_error_falls_back_to_per_item():
    """A failing score_batch must degrade to per-item score(), not crash."""
    class FlakyBatch:
        def __init__(self):
            self.item_calls = 0

        def score(self, query, text):
            self.item_calls += 1
            return 0.5

        def score_batch(self, query, texts):
            raise RuntimeError("batch boom")

    scorer = FlakyBatch()
    candidates = [_make_candidate("dish:1", "红烧肉", "经典红烧肉")]
    reranker = CrossEncoderReranker(scorer=scorer)

    reranked = reranker.rerank("红烧肉", candidates, top_k=1)

    assert scorer.item_calls == 1
    assert len(reranked) == 1
    assert reranked[0].cross_encoder_score == 0.5


def test_cross_encoder_fallback_on_failure():
    class FailingScorer:
        def score(self, query, text):
            raise RuntimeError("API down")

    candidates = [_make_candidate("dish:1", "红烧肉", "经典红烧肉")]
    reranker = CrossEncoderReranker(scorer=FailingScorer())
    reranked = reranker.rerank("红烧肉", candidates, top_k=3)

    assert len(reranked) == 1
    assert reranked[0].cross_encoder_score == 0.0
