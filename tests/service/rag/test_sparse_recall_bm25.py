"""Tests for Issue #11: BM25 engineering fixes.

Covers:
- list_merchants() called once (not twice)
- Inverted index is built (not linear scan)
- TF is precomputed (not list.count())
- BM25 k1/b read from config (not class constants)
- Multi-query merges via RRF (not max score)
- Query deduplication before search
- per_query top_k is distributed, not full limit
- Source type filtering
- Ranks are sequential by RRF score
- Limit caps output
- Edge cases: empty index, no queries, fallback to normalized_query
"""

import math
from unittest.mock import patch

from service.config import AppConfig, set_config
from service.rag.models import RagQueryPlan, RecallCandidate
from service.rag.recall import SparseVectorRecallRoute


# ── Fake catalog ──────────────────────────────────────────────────────


class FakeCatalogService:
    """Minimal catalog service that records calls and returns fixed data."""

    def __init__(self, merchants=None, dishes_by_merchant=None):
        self._merchants = merchants or []
        self._dishes_by_merchant = dishes_by_merchant or {}
        self.list_merchants_call_count = 0

    def list_merchants(self):
        self.list_merchants_call_count += 1
        return list(self._merchants)

    def list_dishes_by_merchant(self, merchant_id):
        return list(self._dishes_by_merchant.get(merchant_id, []))


def _merchant(mid: int, name: str, **extra) -> dict:
    return {
        "id": mid, "name": name,
        "description": f"desc_{name}", "rating": 4.5,
        **extra,
    }


def _dish(did: int, name: str, merchant_id: int, **extra) -> dict:
    return {
        "id": did, "name": name, "merchant_id": merchant_id,
        "description": f"desc_{name}",
        "cuisine_type": "中餐", "flavor_profile": "鲜香",
        "tags": [], "ingredients": [], "is_available": True,
        **extra,
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


# ── Fixture ───────────────────────────────────────────────────────────


def _build_simple_route():
    """Route with 2 merchants and 3 dishes."""
    merchants = [_merchant(1, "兰姨小炒"), _merchant(2, "川味火锅")]
    dishes = {
        1: [_dish(10, "宫保鸡丁", 1), _dish(11, "麻婆豆腐", 1)],
        2: [_dish(20, "水煮鱼", 2)],
    }
    svc = FakeCatalogService(merchants, dishes)
    route = SparseVectorRecallRoute(svc)
    route.build_index()
    return route, svc


# ── list_merchants called once ────────────────────────────────────────


def test_list_merchants_called_once() -> None:
    """build_index should call list_merchants() exactly once, not twice."""
    route, svc = _build_simple_route()
    assert svc.list_merchants_call_count == 1


def test_recall_does_not_rebuild_when_already_built() -> None:
    """Repeated recalls on a built route must not trigger another full
    catalog scan / index rebuild."""
    route, svc = _build_simple_route()
    assert svc.list_merchants_call_count == 1

    route.recall(_plan(), limit=5)
    route.recall(_plan(), limit=5)

    assert svc.list_merchants_call_count == 1


# ── Inverted index ────────────────────────────────────────────────────


def test_inverted_index_built() -> None:
    """After build_index, _inverted should map tokens to doc indices."""
    route, _ = _build_simple_route()
    assert len(route._inverted) > 0
    for token, doc_indices in route._inverted.items():
        for idx in doc_indices:
            assert 0 <= idx < route._N


def test_inverted_index_contains_jieba_tokens_and_unigrams() -> None:
    """Domain words should appear as whole tokens; characters as unigram fallback."""
    route, _ = _build_simple_route()
    # "宫保鸡丁" is a domain word → kept as one jieba token
    assert "宫保鸡丁" in route._inverted
    # Character unigrams provide sub-word fallback
    assert "宫" in route._inverted
    assert "鸡" in route._inverted


# ── TF precomputed ────────────────────────────────────────────────────


def test_tf_precomputed() -> None:
    """After build_index, _tf[doc_idx] should be a dict of token → count."""
    route, _ = _build_simple_route()
    assert len(route._tf) == route._N
    for tf_dict in route._tf:
        assert isinstance(tf_dict, dict)
        for token, count in tf_dict.items():
            assert isinstance(token, str)
            assert count >= 1


def test_tf_matches_actual_counts() -> None:
    """Precomputed TF should match actual token occurrences."""
    route, _ = _build_simple_route()
    doc_tokens = [route._tokenize(d["text"]) for d in route._docs]
    for doc_idx, tf_dict in enumerate(route._tf):
        for token, count in tf_dict.items():
            assert count == doc_tokens[doc_idx].count(token)


# ── BM25 params from config ──────────────────────────────────────────


def test_bm25_score_accepts_k1_b_params() -> None:
    """_bm25_score should use provided k1/b, producing different scores."""
    route, _ = _build_simple_route()
    query_tokens = route._tokenize("宫保鸡丁")
    doc_idx = next(i for i, d in enumerate(route._docs) if d["source_id"] == 10)

    score_a = route._bm25_score(query_tokens, doc_idx, k1=1.2, b=0.75)
    score_b = route._bm25_score(query_tokens, doc_idx, k1=2.0, b=0.3)

    assert score_a > 0
    assert score_b > 0
    assert score_a != score_b


def test_recall_reads_config_bm25_params() -> None:
    """recall() reads BM25 k1/b from get_config().rag, not class constants."""
    route, _ = _build_simple_route()
    plan = _plan(expansion_queries=["宫保鸡丁"], source_types=["dish"])

    cfg = AppConfig()
    cfg.rag.bm25_k1 = 3.0
    cfg.rag.bm25_b = 0.2

    with patch("service.rag.recall.get_config", return_value=cfg) as mock_cfg:
        result = route.recall(plan, limit=10)

    # get_config must be called during BM25 scoring
    assert mock_cfg.call_count >= 1
    assert len(result) > 0


# ── No class-level BM25 constants ─────────────────────────────────────


def test_no_hardcoded_bm25_class_constants() -> None:
    """_BM25_K1 and _BM25_B class constants should no longer exist."""
    assert not hasattr(SparseVectorRecallRoute, "_BM25_K1")
    assert not hasattr(SparseVectorRecallRoute, "_BM25_B")


# ── Multi-query RRF merge ────────────────────────────────────────────


def test_multi_query_rrf_boosts_shared_hits() -> None:
    """Candidate found by multiple queries should rank higher via RRF."""
    route, _ = _build_simple_route()
    # Both "宫保鸡丁" and "鸡丁" match dish 10 (宫保鸡丁).
    # "水煮" matches dish 20 (水煮鱼) from only one query.
    plan = _plan(
        expansion_queries=["宫保鸡丁", "鸡丁"],
        source_types=["dish"],
    )

    result = route.recall(plan, limit=10)
    keys = [c.stable_key for c in result]
    assert keys[0] == "dish:10", "Multi-query hit should rank first"


def test_rrf_deduplicates_same_candidate() -> None:
    """Same dish from 2 queries produces only 1 candidate."""
    route, _ = _build_simple_route()
    plan = _plan(
        expansion_queries=["宫保鸡丁", "宫保"],
        source_types=["dish"],
    )

    result = route.recall(plan, limit=50)
    stable_keys = [c.stable_key for c in result]
    assert len(stable_keys) == len(set(stable_keys))


# ── Query deduplication ───────────────────────────────────────────────


def test_duplicate_queries_deduplicated() -> None:
    """Identical queries should be deduplicated before search."""
    route, _ = _build_simple_route()

    original_bm25_query = route._bm25_query
    call_count = 0

    def counting_bm25_query(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original_bm25_query(*args, **kwargs)

    route._bm25_query = counting_bm25_query

    plan = _plan(expansion_queries=["测试", "测试", "其他"], source_types=["dish"])
    route.recall(plan, limit=10)

    assert call_count == 2  # "测试" deduplicated → 2 unique queries


def test_empty_and_none_queries_skipped() -> None:
    """Empty/None query strings should be filtered out."""
    route, _ = _build_simple_route()
    plan = _plan(expansion_queries=["", None, "宫保"], source_types=["dish"])

    result = route.recall(plan, limit=10)
    assert len(result) > 0


# ── per_query top_k distributed ───────────────────────────────────────


def test_per_query_top_k_distributed() -> None:
    """With 3 queries, per_query top_k = ceil(limit / 3)."""
    route, _ = _build_simple_route()

    original_bm25_query = route._bm25_query
    top_ks: list[int] = []

    def recording_bm25_query(query, source_types, top_k):
        top_ks.append(top_k)
        return original_bm25_query(query, source_types, top_k)

    route._bm25_query = recording_bm25_query

    plan = _plan(expansion_queries=["q1", "q2", "q3"], source_types=["dish"])
    route.recall(plan, limit=50)

    expected = math.ceil(50 / 3)
    assert len(top_ks) == 3
    assert all(tk == expected for tk in top_ks)


def test_single_query_uses_full_limit() -> None:
    """1 query → per_query top_k = limit."""
    route, _ = _build_simple_route()

    original_bm25_query = route._bm25_query
    top_ks: list[int] = []

    def recording_bm25_query(query, source_types, top_k):
        top_ks.append(top_k)
        return original_bm25_query(query, source_types, top_k)

    route._bm25_query = recording_bm25_query

    plan = _plan(expansion_queries=["q1"], source_types=["dish"])
    route.recall(plan, limit=50)

    assert len(top_ks) == 1
    assert top_ks[0] == 50


# ── Source type filtering ─────────────────────────────────────────────


def test_source_type_dish_only() -> None:
    """source_types=['dish'] should not return merchants."""
    route, _ = _build_simple_route()
    plan = _plan(expansion_queries=["兰姨"], source_types=["dish"])

    result = route.recall(plan, limit=50)
    for c in result:
        assert c.source_type == "dish"


def test_source_type_merchant_only() -> None:
    """source_types=['merchant'] should not return dishes."""
    route, _ = _build_simple_route()
    plan = _plan(expansion_queries=["兰姨"], source_types=["merchant"])

    result = route.recall(plan, limit=50)
    for c in result:
        assert c.source_type == "merchant"


def test_source_type_both_returns_mixed() -> None:
    """source_types=['dish', 'merchant'] should return both."""
    route, _ = _build_simple_route()
    plan = _plan(expansion_queries=["兰姨"], source_types=["dish", "merchant"])

    result = route.recall(plan, limit=50)
    types = {c.source_type for c in result}
    assert "merchant" in types


# ── Ranks and limit ──────────────────────────────────────────────────


def test_ranks_are_sequential() -> None:
    """Output ranks should be 1, 2, 3... based on RRF score."""
    route, _ = _build_simple_route()
    plan = _plan(expansion_queries=["中餐"], source_types=["dish", "merchant"])

    result = route.recall(plan, limit=50)
    for i, c in enumerate(result):
        assert c.rank == i + 1


def test_limit_caps_output() -> None:
    """Output should not exceed limit."""
    route, _ = _build_simple_route()
    plan = _plan(expansion_queries=["中餐"], source_types=["dish", "merchant"])

    result = route.recall(plan, limit=2)
    assert len(result) <= 2


# ── Edge cases ────────────────────────────────────────────────────────


def test_empty_index_returns_empty() -> None:
    """Empty catalog should return empty results."""
    svc = FakeCatalogService([], {})
    route = SparseVectorRecallRoute(svc)
    route.build_index()

    result = route.recall(_plan(), limit=10)
    assert result == []


def test_no_queries_returns_empty() -> None:
    """Empty queries + empty normalized_query should return empty."""
    route, _ = _build_simple_route()
    plan = _plan(expansion_queries=[], normalized_query="")

    result = route.recall(plan, limit=10)
    assert result == []


def test_fallback_to_normalized_query() -> None:
    """When expansion_queries is empty, use normalized_query."""
    route, _ = _build_simple_route()
    plan = _plan(expansion_queries=[], normalized_query="宫保鸡丁", source_types=["dish"])

    result = route.recall(plan, limit=10)
    assert len(result) > 0
    assert result[0].stable_key == "dish:10"


def test_no_matching_tokens_returns_empty() -> None:
    """Query with tokens not in any document should return empty."""
    route, _ = _build_simple_route()
    plan = _plan(expansion_queries=["ZZZZZZZ"], source_types=["dish"])

    result = route.recall(plan, limit=10)
    assert result == []


def test_auto_build_on_first_recall() -> None:
    """If build_index was not called, recall() should auto-build."""
    merchants = [_merchant(1, "测试店")]
    dishes = {1: [_dish(10, "测试菜", 1)]}
    svc = FakeCatalogService(merchants, dishes)
    route = SparseVectorRecallRoute(svc)

    assert not route._built
    result = route.recall(
        _plan(expansion_queries=["测试"], source_types=["dish"]),
        limit=10,
    )
    assert route._built
    assert len(result) > 0


# ── Jieba tokenizer tests ─────────────────────────────────────────────


def test_tokenizer_built_with_domain_words() -> None:
    """build_index should create a jieba tokenizer with domain vocabulary."""
    route, _ = _build_simple_route()
    assert route._tokenizer is not None


def test_domain_word_kept_as_single_token() -> None:
    """Dish names added to domain dict should be kept intact by jieba."""
    route, _ = _build_simple_route()
    tokens = route._tokenize("宫保鸡丁")
    # "宫保鸡丁" should appear as one token (domain word)
    assert "宫保鸡丁" in tokens


def test_unigram_fallback_for_sub_word_matching() -> None:
    """Character unigrams appended for multi-char tokens enable partial matches."""
    route, _ = _build_simple_route()
    tokens = route._tokenize("宫保鸡丁")
    # Individual characters should be present as fallback
    assert "鸡" in tokens
    assert "丁" in tokens


def test_partial_query_matches_full_term_via_unigrams() -> None:
    """A sub-word query like '鸡丁' should match doc containing '宫保鸡丁'."""
    route, _ = _build_simple_route()
    plan = _plan(expansion_queries=["鸡丁"], source_types=["dish"])

    result = route.recall(plan, limit=10)
    keys = [c.stable_key for c in result]
    assert "dish:10" in keys, "Partial query '鸡丁' should match '宫保鸡丁' via unigrams"


def test_bigram_fallback_when_tokenizer_is_none() -> None:
    """Without jieba tokenizer, _tokenize should fall back to bigrams."""
    route, _ = _build_simple_route()
    route._tokenizer = None  # Simulate no jieba

    tokens = route._tokenize("宫保鸡丁")
    # Bigram fallback: "宫保", "保鸡", "鸡丁" should appear
    assert "宫保" in tokens
    assert "鸡丁" in tokens


def test_empty_text_returns_empty_tokens() -> None:
    route, _ = _build_simple_route()
    assert route._tokenize("") == []
    assert route._tokenize(None) == []


def test_tokenizer_not_shared_across_instances() -> None:
    """Each SparseVectorRecallRoute should have its own tokenizer."""
    merchants = [_merchant(1, "店铺A")]
    dishes_a = {1: [_dish(10, "独特菜名AAA", 1)]}
    dishes_b = {1: [_dish(20, "独特菜名BBB", 1)]}

    route_a = SparseVectorRecallRoute(FakeCatalogService(merchants, dishes_a))
    route_a.build_index()
    route_b = SparseVectorRecallRoute(FakeCatalogService(merchants, dishes_b))
    route_b.build_index()

    # Each tokenizer should have different domain words
    tokens_a = route_a._tokenize("独特菜名AAA")
    tokens_b = route_b._tokenize("独特菜名BBB")
    assert "独特菜名AAA" in tokens_a
    assert "独特菜名BBB" in tokens_b
