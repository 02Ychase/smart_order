from __future__ import annotations

import logging
import math
import os
from http import HTTPStatus

import dashscope
from langsmith import traceable

from service.cache import TieredCache
from service.config import get_config
from service.rag.models import FusedCandidate, RagQueryPlan

logger = logging.getLogger(__name__)

# Embedding configuration (shared with AssistantVectorStore)
_EMBEDDING_MODEL = "text-embedding-v4"
_EMBEDDING_DIMENSION = 1536
_EMBEDDING_SIMILARITY_THRESHOLD = 0.70
_EMBEDDING_CACHE_SIZE = 2048

# Feature flag: set to "legacy" to use keyword matching, "embedding" for embedding-based
_EMBEDDING_MODE = os.getenv("USER_PREF_MATCH_MODE", "embedding")

INTENT_WEIGHTS: dict[str, dict[str, float]] = get_config().rag.intent_weights


class WeightedReranker:
    def _get_weights_for_intent(self, intent: str) -> dict[str, float]:
        """Return the weight profile for a given intent, falling back to 'default'."""
        config = get_config().rag
        weights = config.intent_weights
        return weights.get(intent, weights.get("default", {}))

    @traceable(name="weighted_rerank")
    def rerank(
        self,
        candidates: list[FusedCandidate],
        original_query: str,
        query_plan: RagQueryPlan | None = None,
        memories: list[dict] | None = None,
    ) -> list[FusedCandidate]:
        intent = query_plan.answer_mode if query_plan else "default"
        weights = self._get_weights_for_intent(intent)

        should = (query_plan.should_filters if query_plan else {}) or {}
        should_cuisine = should.get("cuisine_types") or []
        should_flavors = should.get("flavor_preferences") or []

        preferred_dishes = query_plan.preferred_dishes if query_plan else []
        preferred_merchants = query_plan.preferred_merchants if query_plan else []

        for candidate in candidates:
            candidate.constraint_match = _calc_constraint_match(candidate, should_cuisine, should_flavors)
            user_pref_score = _calc_user_preference_match(
                candidate, memories or [], preferred_dishes, preferred_merchants
            )
            candidate.facts["user_preference_match"] = user_pref_score

            merchant_rating = float(candidate.facts.get("merchant_rating") or 0.0) / 5.0
            business_boost = 1.0 if candidate.facts.get("is_recommended") else 0.0

            candidate.final_score = (
                weights["dense"] * candidate.dense_score
                + weights["lexical"] * candidate.lexical_score
                + weights["constraint"] * candidate.constraint_match
                + weights["rating"] * merchant_rating
                + weights["business"] * business_boost
                + weights["user_pref"] * user_pref_score
                + weights.get("cross_encoder", 0.0) * candidate.cross_encoder_score
            )
        return sorted(candidates, key=lambda item: item.final_score, reverse=True)


def _calc_constraint_match(candidate: FusedCandidate, cuisine_types: list[str], flavor_prefs: list[str]) -> float:
    if not cuisine_types and not flavor_prefs:
        return 1.0

    hits = 0
    total = 0
    facts = candidate.facts

    if cuisine_types:
        total += 1
        cuisine = str(facts.get("cuisine_type") or "")
        category = str(facts.get("homepage_category") or "")
        combined = f"{cuisine} {category}"
        if any(item in combined for item in cuisine_types):
            hits += 1

    if flavor_prefs:
        total += 1
        flavor_text = " ".join([
            str(facts.get("flavor_profile") or ""),
            str(facts.get("description") or ""),
            str(facts.get("dish_name") or ""),
            str(facts.get("name") or ""),
        ])
        if any(pref in flavor_text for pref in flavor_prefs):
            hits += 1

    if total == 0:
        return 1.0
    return 0.3 + 0.7 * (hits / total)


def _calc_user_preference_match(
    candidate: FusedCandidate,
    memories: list[dict],
    preferred_dishes: list[str] | None = None,
    preferred_merchants: list[str] | None = None,
) -> float:
    if not memories and not preferred_dishes and not preferred_merchants:
        return 0.0

    facts = candidate.facts
    candidate_text = " ".join(
        str(facts.get(k, ""))
        for k in ("cuisine_type", "flavor_profile", "dish_name", "name",
                   "merchant_name", "description", "homepage_category")
    )

    score = 0.0
    weight_sum = 0.0
    for mem in memories:
        content = str(mem.get("content", ""))
        confidence = float(mem.get("confidence", 0.5))
        if not content:
            continue
        weight_sum += confidence
        if _text_overlaps(content, candidate_text):
            score += confidence

    if preferred_dishes:
        dish_name = str(facts.get("dish_name", "") or facts.get("name", ""))
        for pref_dish in preferred_dishes:
            if pref_dish in dish_name or dish_name in pref_dish:
                score += 1.0
                weight_sum += 1.0

    if preferred_merchants:
        merchant_name = str(facts.get("merchant_name", "") or facts.get("name", ""))
        for pref_merchant in preferred_merchants:
            if pref_merchant in merchant_name or merchant_name in pref_merchant:
                score += 1.0
                weight_sum += 1.0

    if weight_sum == 0:
        return 0.0
    return score / weight_sum


_embedding_cache = TieredCache(l1_max_size=_EMBEDDING_CACHE_SIZE)


def _get_embedding_cached(text: str) -> tuple[float, ...] | None:
    """Get embedding vector for text via DashScope, cached by TieredCache."""
    cached = _embedding_cache.get(text)
    if cached is not None:
        return cached

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.warning("DASHSCOPE_API_KEY not set — embedding unavailable")
        return None
    try:
        resp = dashscope.TextEmbedding.call(
            model=_EMBEDDING_MODEL,
            input=text,
            dimension=_EMBEDDING_DIMENSION,
            api_key=api_key,
        )
        if resp["status_code"] == HTTPStatus.OK:
            embedding = resp.get("output", {}).get("embeddings", [{}])[0].get("embedding")
            if embedding and len(embedding) == _EMBEDDING_DIMENSION:
                result = tuple(embedding)
                _embedding_cache.set(text, result)
                return result
        logger.error(f"Embedding request failed: status={resp.get('status_code')}")
        return None
    except Exception as e:
        logger.error(f"Embedding request failed: {e}")
        return None


# Expose cache_clear for backward compatibility with tests
def cache_clear():
    _embedding_cache.clear()


def cosine_similarity(vec1: list[float] | tuple[float, ...], vec2: list[float] | tuple[float, ...]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def _text_overlaps_legacy(memory_content: str, candidate_text: str) -> bool:
    """Keyword-based matching (35 Chinese cuisine keywords). Kept as fallback."""
    keywords = ["湘菜", "川菜", "粤菜", "鲁菜", "苏菜", "闽菜", "浙菜", "徽菜",
                "辣", "麻", "酸", "甜", "苦", "咸", "清淡", "香", "鲜",
                "面", "粉", "饭", "汤", "锅", "煲", "烧", "烤", "蒸", "炒",
                "鸡", "鸭", "鱼", "虾", "蟹", "牛", "羊", "猪",
                "咖啡", "茶", "奶茶", "甜点", "蛋糕",
                "素食", "清真"]
    for kw in keywords:
        if kw in memory_content and kw in candidate_text:
            return True
    return False


def _text_overlaps_embedding(memory_content: str, candidate_text: str) -> bool | None:
    """Check semantic overlap using embedding cosine similarity.

    Returns None when embedding is unavailable (API key missing, service error),
    allowing the caller to fall back to keyword matching.
    """
    mem_emb = _get_embedding_cached(memory_content)
    cand_emb = _get_embedding_cached(candidate_text)
    if mem_emb is None or cand_emb is None:
        return None
    sim = cosine_similarity(list(mem_emb), list(cand_emb))
    return sim >= _EMBEDDING_SIMILARITY_THRESHOLD


def _text_overlaps(memory_content: str, candidate_text: str) -> bool:
    """Unified entry point for text overlap detection.

    Uses embedding-based similarity by default. Falls back to keyword matching
    when embedding is unavailable (e.g., DASHSCOPE_API_KEY not set).
    Mode is read per-call so runtime/test env var changes take effect.
    """
    mode = os.getenv("USER_PREF_MATCH_MODE", "embedding")
    if mode == "legacy":
        return _text_overlaps_legacy(memory_content, candidate_text)
    result = _text_overlaps_embedding(memory_content, candidate_text)
    if result is not None:
        return result
    # Fallback to keyword matching when embedding is unavailable
    return _text_overlaps_legacy(memory_content, candidate_text)
