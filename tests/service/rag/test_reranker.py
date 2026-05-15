from unittest.mock import MagicMock, patch

from service.rag.models import FusedCandidate, RagQueryPlan
from service.rag.reranker import (
    INTENT_WEIGHTS,
    WeightedReranker,
    _calc_user_preference_match,
    _get_embedding_cached,
    _text_overlaps,
    _text_overlaps_embedding,
    cache_clear,
    _text_overlaps_legacy,
    cosine_similarity,
)


def test_weighted_reranker_prefers_relevance_and_constraints() -> None:
    candidates = [
        FusedCandidate(stable_key="dish:1", source_type="dish", source_id=1, facts={"merchant_rating": 4.9}, dense_score=0.2, lexical_score=0.1, constraint_match=0.2),
        FusedCandidate(stable_key="dish:2", source_type="dish", source_id=2, facts={"merchant_rating": 4.5}, dense_score=0.8, lexical_score=0.7, constraint_match=1.0),
    ]

    ranked = WeightedReranker().rerank(candidates, original_query="辣的湘菜")

    assert ranked[0].stable_key == "dish:2"
    assert ranked[0].final_score > ranked[1].final_score


# ── Dynamic weight adjustment tests ──────────────────────────────────────────


def test_recommendation_intent_uses_higher_constraint_and_rating_weights() -> None:
    weights = INTENT_WEIGHTS["recommendation"]

    assert weights["constraint"] > INTENT_WEIGHTS["default"]["constraint"]
    assert weights["rating"] > INTENT_WEIGHTS["default"]["rating"]
    assert weights["dense"] < INTENT_WEIGHTS["default"]["dense"]
    assert weights["lexical"] < INTENT_WEIGHTS["default"]["lexical"]


def test_knowledge_intent_uses_higher_dense_and_lexical_weights() -> None:
    weights = INTENT_WEIGHTS["knowledge"]

    assert weights["dense"] > INTENT_WEIGHTS["default"]["dense"]
    assert weights["lexical"] > INTENT_WEIGHTS["default"]["lexical"]
    assert weights["constraint"] < INTENT_WEIGHTS["default"]["constraint"]
    assert weights["business"] < INTENT_WEIGHTS["default"]["business"]


def test_fallback_to_default_weights_for_unknown_intent() -> None:
    reranker = WeightedReranker()

    assert reranker._get_weights_for_intent("greeting") == INTENT_WEIGHTS["default"]
    assert reranker._get_weights_for_intent("cart_action") == INTENT_WEIGHTS["default"]
    assert reranker._get_weights_for_intent("bogus_intent") == INTENT_WEIGHTS["default"]


def test_scoring_formula_uses_intent_based_weights() -> None:
    candidates = [
        FusedCandidate(
            stable_key="dish:1",
            source_type="dish",
            source_id=1,
            facts={"merchant_rating": 4.9, "is_recommended": True},
            dense_score=0.5,
            lexical_score=0.5,
            constraint_match=0.5,
        ),
    ]

    plan = RagQueryPlan(
        original_query="推荐辣的湘菜",
        normalized_query="辣的湘菜",
        answer_mode="recommendation",
    )
    weights = INTENT_WEIGHTS["recommendation"]

    ranked = WeightedReranker().rerank(candidates, original_query="辣的湘菜", query_plan=plan)
    candidate = ranked[0]

    expected_score = (
        weights["dense"] * candidate.dense_score
        + weights["lexical"] * candidate.lexical_score
        + weights["constraint"] * candidate.constraint_match
        + weights["rating"] * (4.9 / 5.0)
        + weights["business"] * 1.0
        + weights["user_pref"] * 0.0
    )
    assert abs(candidate.final_score - expected_score) < 0.001


def test_default_intent_when_no_query_plan_provided() -> None:
    candidates = [
        FusedCandidate(
            stable_key="dish:1",
            source_type="dish",
            source_id=1,
            facts={"merchant_rating": 4.5},
            dense_score=1.0,
            lexical_score=0.0,
            constraint_match=1.0,
        ),
    ]

    ranked = WeightedReranker().rerank(candidates, original_query="辣的湘菜")
    candidate = ranked[0]

    w = INTENT_WEIGHTS["default"]
    expected_score = (
        w["dense"] * 1.0
        + w["lexical"] * 0.0
        + w["constraint"] * 1.0
        + w["rating"] * (4.5 / 5.0)
        + w["business"] * 0.0
        + w["user_pref"] * 0.0
    )
    assert abs(candidate.final_score - expected_score) < 0.001


def test_all_weights_sum_to_one() -> None:
    for intent, weights in INTENT_WEIGHTS.items():
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001, f"{intent} weights sum to {total}, expected 1.0"


# ── Cosine similarity tests ──────────────────────────────────────────────────


def test_cosine_similarity_identical_vectors() -> None:
    vec = [1.0, 2.0, 3.0]
    assert abs(cosine_similarity(vec, vec) - 1.0) < 0.0001


def test_cosine_similarity_orthogonal_vectors() -> None:
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0]) - 0.0) < 0.0001


def test_cosine_similarity_opposite_vectors() -> None:
    assert abs(cosine_similarity([1.0, 2.0], [-1.0, -2.0]) + 1.0) < 0.0001


def test_cosine_similarity_different_lengths_returns_zero() -> None:
    assert cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0


def test_cosine_similarity_zero_vector() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0


def test_cosine_similarity_positive_correlation() -> None:
    sim = cosine_similarity([1.0, 0.5, 0.0], [0.8, 0.4, 0.0])
    assert sim > 0.99


# ── Legacy keyword overlap tests ─────────────────────────────────────────────


def test_text_overlaps_legacy_matches_shared_keyword() -> None:
    assert _text_overlaps_legacy("我喜欢吃川菜", "川味麻辣 鱼香肉丝") is True


def test_text_overlaps_legacy_no_shared_keyword() -> None:
    assert _text_overlaps_legacy("我喜欢清淡口味", "麻辣火锅") is False


def test_text_overlaps_legacy_matches_cuisine_keyword() -> None:
    assert _text_overlaps_legacy("爱吃湘菜", "湘菜 小炒黄牛肉") is True


# ── Embedding-based overlap tests ────────────────────────────────────────────


def _make_embedding_mock(similarity: float, dimension: int = 1536):
    """Create a mock response that produces embeddings with the given cosine similarity."""
    import math
    base = [0.05] * dimension
    base[0] = 1.0

    if similarity > 0.999:
        second = base[:]
    else:
        second = [0.05] * dimension
        second[0] = similarity

    call_count = [0]

    def mock_embedding(model=None, input=None, dimension=None, api_key=None):
        if call_count[0] == 0:
            call_count[0] += 1
            mock_resp = MagicMock()
            mock_resp.__getitem__ = MagicMock(return_value=200)
            mock_resp.get.side_effect = lambda key, default=None: {
                "output": {"embeddings": [{"embedding": base}]}
            }.get(key, default)
            return mock_resp
        else:
            call_count[0] += 1
            mock_resp = MagicMock()
            mock_resp.__getitem__ = MagicMock(return_value=200)
            mock_resp.get.side_effect = lambda key, default=None: {
                "output": {"embeddings": [{"embedding": second}]}
            }.get(key, default)
            return mock_resp

    return mock_embedding


def test_text_overlaps_embedding_high_similarity(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    mock_embed = _make_embedding_mock(similarity=0.90)

    with patch("service.rag.reranker._get_embedding_cached", wraps=None) as mock_cached:
        cache_clear()
        with patch("service.rag.reranker.dashscope.TextEmbedding.call", side_effect=mock_embed):
            # Force fresh cache by calling the embedding function directly
            result = _text_overlaps_embedding("我爱吃辣的川菜", "川味麻辣 鱼香肉丝")

    assert result is True


def test_text_overlaps_embedding_low_similarity(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    mock_embed = _make_embedding_mock(similarity=0.20)

    cache_clear()
    with patch("service.rag.reranker.dashscope.TextEmbedding.call", side_effect=mock_embed):
        result = _text_overlaps_embedding("我爱吃辣的川菜", "清淡粤菜 白切鸡")

    assert result is False


def test_text_overlaps_embedding_no_api_key_returns_none(monkeypatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    cache_clear()
    result = _text_overlaps_embedding("anything", "anything else")
    assert result is None


# ── Unified _text_overlaps mode switching ────────────────────────────────────


def test_text_overlaps_uses_embedding_mode_by_default(monkeypatch) -> None:
    monkeypatch.setenv("USER_PREF_MATCH_MODE", "embedding")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    cache_clear()

    with patch("service.rag.reranker._text_overlaps_embedding", return_value=True) as mock_emb:
        with patch("service.rag.reranker._text_overlaps_legacy", return_value=False) as mock_leg:
            result = _text_overlaps("content", "candidate text")
    assert result is True
    mock_emb.assert_called_once()
    mock_leg.assert_not_called()


def test_text_overlaps_falls_back_to_keyword_when_embedding_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("USER_PREF_MATCH_MODE", "embedding")
    cache_clear()

    with patch("service.rag.reranker._text_overlaps_embedding", return_value=None) as mock_emb:
        with patch("service.rag.reranker._text_overlaps_legacy", return_value=True) as mock_leg:
            result = _text_overlaps("content", "candidate text")
    assert result is True
    mock_emb.assert_called_once()
    mock_leg.assert_called_once()


def test_text_overlaps_uses_legacy_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("USER_PREF_MATCH_MODE", "legacy")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    cache_clear()

    with patch("service.rag.reranker._text_overlaps_embedding", return_value=True) as mock_emb:
        with patch("service.rag.reranker._text_overlaps_legacy", return_value=True) as mock_leg:
            result = _text_overlaps("content", "candidate text")
    assert result is True
    mock_leg.assert_called_once()
    mock_emb.assert_not_called()


# ── User preference matching with embedding similarity ───────────────────────


def _make_fused_candidate(**facts) -> FusedCandidate:
    defaults = {
        "cuisine_type": "川味麻辣",
        "flavor_profile": "香辣",
        "dish_name": "鱼香肉丝",
        "name": "鱼香肉丝",
        "merchant_name": "兰姨小炒",
        "description": "酸甜微辣，下饭",
        "homepage_category": "湘菜",
    }
    defaults.update(facts)
    return FusedCandidate(
        stable_key="dish:1",
        source_type="dish",
        source_id=1,
        facts=defaults,
    )


def test_user_pref_match_returns_zero_with_no_memories() -> None:
    candidate = _make_fused_candidate()
    score = _calc_user_preference_match(candidate, [])
    assert score == 0.0


def test_user_pref_match_scores_high_similarity_memories_higher(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    cache_clear()

    memories = [
        {"content": "我喜欢吃辣的川菜", "confidence": 0.9},
        {"content": "喜欢粤菜清淡口味", "confidence": 0.8},
    ]
    candidate = _make_fused_candidate()

    # Track which memory-contents are queried
    queried_texts = []

    def fake_overlaps(mem_content, cand_text):
        queried_texts.append(mem_content)
        if "川菜" in mem_content or "辣" in mem_content:
            return True
        return False

    with patch("service.rag.reranker._text_overlaps", side_effect=fake_overlaps):
        score = _calc_user_preference_match(candidate, memories)

    # Memory 1 matches, memory 2 doesn't
    # score = 0.9 / (0.9 + 0.8) = 0.529...
    assert 0.5 < score < 1.0
    assert len(queried_texts) == 2


def test_user_pref_match_all_high_similarity_gives_high_score(monkeypatch) -> None:
    memories = [
        {"content": "爱吃香辣的口味", "confidence": 0.9},
    ]
    candidate = _make_fused_candidate()

    def fake_overlaps(mem_content, cand_text):
        return True

    with patch("service.rag.reranker._text_overlaps", side_effect=fake_overlaps):
        score = _calc_user_preference_match(candidate, memories)

    assert abs(score - 1.0) < 0.001


def test_user_pref_match_all_low_similarity_gives_zero_score(monkeypatch) -> None:
    memories = [
        {"content": "喜欢甜点蛋糕", "confidence": 0.9},
        {"content": "喜欢清淡素食", "confidence": 0.7},
    ]
    candidate = _make_fused_candidate()

    def fake_overlaps(mem_content, cand_text):
        return False

    with patch("service.rag.reranker._text_overlaps", side_effect=fake_overlaps):
        score = _calc_user_preference_match(candidate, memories)

    assert score == 0.0


def test_user_pref_match_weights_by_confidence(monkeypatch) -> None:
    def fake_overlaps(mem_content, cand_text):
        return True

    # High-confidence memory should dominate
    high_conf = [
        {"content": "爱吃辣", "confidence": 0.95},
        {"content": "喜欢清淡", "confidence": 0.1},
    ]
    candidate = _make_fused_candidate()

    with patch("service.rag.reranker._text_overlaps", side_effect=fake_overlaps):
        score = _calc_user_preference_match(candidate, high_conf)

    # All memories match, so score = (0.95 + 0.1) / (0.95 + 0.1) = 1.0
    assert abs(score - 1.0) < 0.001

    # Low-confidence memories should produce lower score when matching is partial
    low_conf = [
        {"content": "爱吃辣", "confidence": 0.2},
        {"content": "喜欢清淡", "confidence": 0.1},
    ]

    def partial_overlaps(mem_content, cand_text):
        return "辣" in mem_content

    with patch("service.rag.reranker._text_overlaps", side_effect=partial_overlaps):
        score = _calc_user_preference_match(candidate, low_conf)

    # Only first memory matches: 0.2 / (0.2 + 0.1) = 0.666...
    assert 0.6 < score < 0.7


def test_user_pref_match_skips_empty_memory_content(monkeypatch) -> None:
    memories = [
        {"content": "", "confidence": 0.9},
        {"content": "爱吃辣", "confidence": 0.8},
    ]
    candidate = _make_fused_candidate()

    def fake_overlaps(mem_content, cand_text):
        return True

    with patch("service.rag.reranker._text_overlaps", side_effect=fake_overlaps):
        score = _calc_user_preference_match(candidate, memories)

    # Only the non-empty memory counts, all match: 0.8 / 0.8 = 1.0
    assert abs(score - 1.0) < 0.001


def test_user_pref_match_fact_in_candidate_facts_dict(monkeypatch) -> None:
    """Verify user_preference_match is stored in candidate.facts."""
    candidate = _make_fused_candidate()
    memories = [{"content": "爱吃辣", "confidence": 0.9}]

    def fake_overlaps(mem_content, cand_text):
        return True

    with patch("service.rag.reranker._text_overlaps", side_effect=fake_overlaps):
        WeightedReranker().rerank([candidate], original_query="test", memories=memories)

    assert "user_preference_match" in candidate.facts
    assert candidate.facts["user_preference_match"] > 0.0


# ── Embedding caching tests ──────────────────────────────────────────────────


def test_get_embedding_cached_reuses_results(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    cache_clear()

    fake_embedding = [0.1] * 1536
    mock_resp = MagicMock()
    mock_resp.__getitem__ = MagicMock(return_value=200)
    mock_resp.get.side_effect = lambda key, default=None: {
        "output": {"embeddings": [{"embedding": fake_embedding}]}
    }.get(key, default)

    with patch("service.rag.reranker.dashscope.TextEmbedding.call", return_value=mock_resp) as mock_call:
        result1 = _get_embedding_cached("川菜麻辣")
        result2 = _get_embedding_cached("川菜麻辣")
        result3 = _get_embedding_cached("粤菜清淡")

    assert result1 == result2 == tuple(fake_embedding)
    assert mock_call.call_count == 2  # "川菜麻辣" cached, "粤菜清淡" new call


def test_get_embedding_cached_returns_none_on_api_failure(monkeypatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    cache_clear()

    mock_resp = MagicMock()
    mock_resp.__getitem__ = MagicMock(return_value=500)
    mock_resp.get.return_value = None

    with patch("service.rag.reranker.dashscope.TextEmbedding.call", return_value=mock_resp):
        result = _get_embedding_cached("some text")

    assert result is None


def test_get_embedding_cached_no_api_key(monkeypatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    cache_clear()
    result = _get_embedding_cached("text")
    assert result is None


# ── Preferred dish / merchant boosting tests ─────────────────────────────────


def test_user_pref_match_boosts_preferred_dish() -> None:
    candidate = _make_fused_candidate(dish_name="宫保鸡丁", name="宫保鸡丁")

    score = _calc_user_preference_match(
        candidate, memories=[], preferred_dishes=["宫保鸡丁"]
    )

    assert score > 0.0


def test_user_pref_match_boosts_preferred_merchant() -> None:
    candidate = _make_fused_candidate(merchant_name="麦当劳")

    score = _calc_user_preference_match(
        candidate, memories=[], preferred_merchants=["麦当劳"]
    )

    assert score > 0.0


def test_user_pref_match_preferred_dish_partial_match() -> None:
    candidate = _make_fused_candidate(dish_name="鱼香肉丝炒饭", name="鱼香肉丝炒饭")

    score = _calc_user_preference_match(
        candidate, memories=[], preferred_dishes=["鱼香肉丝"]
    )

    assert score > 0.0


def test_user_pref_match_no_preferred_dish_match_returns_zero() -> None:
    candidate = _make_fused_candidate(dish_name="宫保鸡丁", name="宫保鸡丁")

    score = _calc_user_preference_match(
        candidate, memories=[], preferred_dishes=["麻婆豆腐"]
    )

    assert score == 0.0


def test_user_pref_match_no_preferred_merchant_match_returns_zero() -> None:
    candidate = _make_fused_candidate(merchant_name="海底捞")

    score = _calc_user_preference_match(
        candidate, memories=[], preferred_merchants=["麦当劳"]
    )

    assert score == 0.0


def test_user_pref_match_combined_memory_and_preferred_items() -> None:
    candidate = _make_fused_candidate(
        dish_name="麻婆豆腐",
        name="麻婆豆腐",
        cuisine_type="川菜",
        flavor_profile="麻辣",
    )

    def fake_overlaps(mem_content, cand_text):
        return "川菜" in mem_content

    with patch("service.rag.reranker._text_overlaps", side_effect=fake_overlaps):
        score = _calc_user_preference_match(
            candidate,
            memories=[{"content": "喜欢川菜", "confidence": 0.9}],
            preferred_dishes=["麻婆豆腐"],
        )

    assert score > 0.0


def test_weighted_reranker_uses_preferred_dishes_from_query_plan() -> None:
    candidate = _make_fused_candidate(dish_name="宫保鸡丁", name="宫保鸡丁")

    plan = RagQueryPlan(
        original_query="推荐菜",
        normalized_query="推荐菜",
        answer_mode="recommendation",
        preferred_dishes=["宫保鸡丁"],
    )

    ranked = WeightedReranker().rerank(
        [candidate], original_query="推荐菜", query_plan=plan
    )

    assert ranked[0].facts["user_preference_match"] > 0.0


def test_weighted_reranker_uses_preferred_merchants_from_query_plan() -> None:
    candidate = _make_fused_candidate(
        source_type="merchant", merchant_name="麦当劳"
    )

    plan = RagQueryPlan(
        original_query="推荐店",
        normalized_query="推荐店",
        answer_mode="knowledge",
        preferred_merchants=["麦当劳"],
    )

    ranked = WeightedReranker().rerank(
        [candidate], original_query="推荐店", query_plan=plan
    )

    assert ranked[0].facts["user_preference_match"] > 0.0


def test_preferred_items_increase_final_score() -> None:
    matched = _make_fused_candidate(
        dish_name="宫保鸡丁",
        name="宫保鸡丁",
        dense_score=0.5,
        lexical_score=0.5,
        constraint_match=0.5,
    )
    unmatched = _make_fused_candidate(
        stable_key="dish:2",
        source_id=2,
        dish_name="白切鸡",
        name="白切鸡",
        dense_score=0.5,
        lexical_score=0.5,
        constraint_match=0.5,
    )

    plan = RagQueryPlan(
        original_query="推荐菜",
        normalized_query="推荐菜",
        answer_mode="recommendation",
        preferred_dishes=["宫保鸡丁"],
    )

    ranked = WeightedReranker().rerank(
        [matched, unmatched], original_query="推荐菜", query_plan=plan
    )

    assert ranked[0].stable_key == "dish:1"
    assert ranked[0].final_score > ranked[1].final_score
