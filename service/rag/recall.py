from __future__ import annotations

import logging
import math
import threading

from langsmith import traceable

try:
    import jieba as _jieba_module
except ImportError:  # pragma: no cover
    _jieba_module = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

from service.catalog_service import CatalogService
from service.config import get_config
from service.rag.models import RagQueryPlan, RecallCandidate
from tools.assistant_vector_store import AssistantVectorStore


class DenseVectorRecallRoute:
    requires_db_session: bool = False

    def __init__(self, vector_store: AssistantVectorStore | None = None) -> None:
        self.vector_store = vector_store or AssistantVectorStore()

    @traceable(name="dense_vector_recall")
    def recall(self, plan: RagQueryPlan, limit: int) -> list[RecallCandidate]:
        if not self.vector_store.is_ready():
            return []

        queries = list(dict.fromkeys(
            query for query in (plan.expansion_queries or [plan.normalized_query])
            if query
        ))
        if not queries:
            return []

        namespaces = [
            ns for ns in ("dishes", "merchants")
            if (ns == "dishes" and "dish" in plan.source_types)
            or (ns == "merchants" and "merchant" in plan.source_types)
        ]
        if not namespaces:
            return []

        # Each query × namespace is a sub-route; distribute limit evenly.
        num_searches = len(queries) * len(namespaces)
        per_query = math.ceil(limit / max(num_searches, 1))

        sub_results: list[list[RecallCandidate]] = []
        for query in queries:
            for namespace in namespaces:
                sub_candidates: list[RecallCandidate] = []
                for rank, match in enumerate(
                    self.vector_store.semantic_search(query, top_k=per_query, namespace=namespace), 1,
                ):
                    metadata = match.get("metadata", {})
                    facts = dict(metadata)
                    facts.setdefault("is_available", True)
                    source_type = metadata.get("source_type", "dish")
                    source_id = int(metadata.get("source_id") or metadata.get("dish_id") or metadata.get("merchant_id"))
                    sub_candidates.append(
                        RecallCandidate(
                            stable_key=f"{source_type}:{source_id}",
                            source_type=source_type,
                            source_id=source_id,
                            route="dense",
                            rank=rank,
                            score=float(match.get("score", 0.0)),
                            facts=facts,
                            citation=str(metadata.get("content", ""))[:180],
                        )
                    )
                sub_results.append(sub_candidates)

        return self._rrf_merge(sub_results, limit)

    @staticmethod
    def _rrf_merge(
        sub_results: list[list[RecallCandidate]], limit: int, k: int = 60,
    ) -> list[RecallCandidate]:
        """Lightweight RRF across query × namespace sub-routes.

        Candidates found by multiple sub-routes accumulate a higher RRF
        score, so items that consistently rank well across different
        expansion queries surface to the top.
        """
        rrf_scores: dict[str, float] = {}
        best: dict[str, RecallCandidate] = {}

        for candidates in sub_results:
            for c in candidates:
                rrf_scores[c.stable_key] = rrf_scores.get(c.stable_key, 0.0) + 1.0 / (k + c.rank)
                if c.stable_key not in best or c.score > best[c.stable_key].score:
                    best[c.stable_key] = c

        sorted_keys = sorted(rrf_scores, key=lambda key: rrf_scores[key], reverse=True)
        result: list[RecallCandidate] = []
        for rank, key in enumerate(sorted_keys[:limit], 1):
            candidate = best[key]
            candidate.rank = rank
            result.append(candidate)
        return result


class SqlCatalogRecallRoute:
    requires_db_session: bool = True

    def __init__(self, catalog_service: CatalogService) -> None:
        self.catalog_service = catalog_service
        self._merchant_cache: dict[int, dict] | None = None

    def _build_merchant_cache(self) -> dict[int, dict]:
        if self._merchant_cache is not None:
            return self._merchant_cache
        self._merchant_cache = {
            m["id"]: m
            for m in self.catalog_service.list_merchants_filtered(limit=500)
        }
        return self._merchant_cache

    @traceable(name="sql_catalog_recall")
    def recall(self, plan: RagQueryPlan, limit: int) -> list[RecallCandidate]:
        candidates = []
        cuisine_types = list(plan.should_filters.get("cuisine_types") or [])
        flavor_preferences = list(plan.should_filters.get("flavor_preferences") or [])
        required_keywords = list(plan.must_filters.get("required_keywords") or [])
        forbidden_keywords = list(plan.must_filters.get("forbidden_keywords") or [])
        source_types = set(plan.source_types)

        rank = 1
        recall_limit = max(limit * 3, 50)

        if "merchant" in source_types:
            for merchant in self.catalog_service.list_merchants_filtered(
                cuisine_types=cuisine_types or None,
                required_keywords=required_keywords or None,
                limit=recall_limit,
            ):
                candidates.append(
                    RecallCandidate(
                        stable_key=f"merchant:{merchant['id']}",
                        source_type="merchant",
                        source_id=merchant["id"],
                        route="sql",
                        rank=rank,
                        score=float(merchant.get("rating") or 0.0) / 5.0,
                        facts={**merchant, "merchant_id": merchant["id"], "merchant_name": merchant["name"], "is_available": True},
                        citation=merchant.get("description", ""),
                    )
                )
                rank += 1

        if "dish" in source_types:
            dishes = self.catalog_service.list_dishes_filtered(
                cuisine_types=cuisine_types or None,
                flavor_keywords=flavor_preferences or None,
                required_keywords=required_keywords or None,
                forbidden_keywords=forbidden_keywords or None,
                limit=recall_limit,
            )
            merchant_cache = self._build_merchant_cache()
            for dish in dishes:
                merchant = merchant_cache.get(dish["merchant_id"])
                merchant_name = merchant["name"] if merchant else ""
                merchant_rating = float(merchant.get("rating") or 0.0) if merchant else 0.0
                candidates.append(
                    RecallCandidate(
                        stable_key=f"dish:{dish['id']}",
                        source_type="dish",
                        source_id=dish["id"],
                        route="sql",
                        rank=rank,
                        score=1.0,
                        facts={
                            **dish,
                            "dish_id": dish["id"],
                            "dish_name": dish["name"],
                            "merchant_id": dish["merchant_id"],
                            "merchant_name": merchant_name,
                            "merchant_rating": merchant_rating,
                            "is_available": dish.get("is_available", True),
                        },
                        citation=dish.get("description", ""),
                    )
                )
                rank += 1
        return candidates[:limit]


class BusinessRecallRoute:
    requires_db_session: bool = True

    def __init__(self, catalog_service: CatalogService) -> None:
        self.catalog_service = catalog_service

    @traceable(name="business_recall")
    def recall(self, plan: RagQueryPlan, limit: int) -> list[RecallCandidate]:
        # Skip dish recommendations when only merchant data is requested
        if plan.source_types and "dish" not in plan.source_types:
            return []

        candidates = []
        dishes = self.catalog_service.list_recommended_dishes(limit=max(limit, 30))

        merchant_cache: dict[int, dict | None] = {}

        def _get_merchant(merchant_id: int) -> dict | None:
            if merchant_id not in merchant_cache:
                merchant_cache[merchant_id] = self.catalog_service.get_merchant(merchant_id)
            return merchant_cache[merchant_id]

        normalized_query = (plan.normalized_query or "").lower()

        for dish in dishes:
            merchant_id = dish["merchant_id"]
            merchant = _get_merchant(merchant_id)

            merchant_name = merchant["name"] if merchant else ""
            merchant_rating = float(merchant.get("rating", 0.0)) if merchant else 0.0

            base_score = 0.7
            rating_bonus = (merchant_rating / 5.0) * 0.2

            query_relevance = 0.0
            dish_name = dish.get("name", "").lower()
            dish_tags = " ".join(dish.get("tags", [])).lower()
            merchant_name_lower = merchant_name.lower()

            if normalized_query:
                query_words = normalized_query.split()
                for word in query_words:
                    if word and (word in dish_name or word in dish_tags or word in merchant_name_lower):
                        query_relevance = 0.1
                        break

            final_score = min(base_score + rating_bonus + query_relevance, 1.0)

            candidates.append(
                RecallCandidate(
                    stable_key=f"dish:{dish['id']}",
                    source_type="dish",
                    source_id=dish["id"],
                    route="business",
                    rank=len(candidates) + 1,
                    score=final_score,
                    facts={
                        **dish,
                        "dish_id": dish["id"],
                        "dish_name": dish["name"],
                        "merchant_id": dish["merchant_id"],
                        "merchant_name": merchant_name,
                        "merchant_rating": merchant_rating,
                        "is_available": True,
                    },
                    citation=dish.get("description", ""),
                )
            )

        return candidates[:limit]


class SparseVectorRecallRoute:
    """BM25 sparse-vector recall with inverted index and jieba segmentation.

    Uses *jieba* with a domain-specific dictionary (dish names, merchant
    names, ingredients, tags) for tokenization.  Character unigrams are
    appended as fallback so partial / abbreviated queries still match.
    Falls back to character bigrams when jieba is not installed.

    Multiple expansion queries are merged via RRF (consistent with
    DenseVectorRecallRoute).
    """

    requires_db_session: bool = True

    def __init__(self, catalog_service: CatalogService) -> None:
        self.catalog_service = catalog_service
        self._docs: list[dict] = []
        self._doc_lengths: list[int] = []
        self._avgdl: float = 0.0
        self._df: dict[str, int] = {}
        self._tf: list[dict[str, int]] = []           # tf[doc_idx][token] = count
        self._inverted: dict[str, list[int]] = {}      # token → [doc_idx, ...]
        self._N: int = 0
        self._tokenizer = None                         # jieba.Tokenizer (built in build_index)
        self._built: bool = False
        self._build_lock = threading.Lock()

    # ── index ────────────────────────────────────────────────────────

    def build_index(self) -> None:
        """Build in-memory BM25 index from all catalog data."""
        docs: list[dict] = []

        merchants = self.catalog_service.list_merchants()

        for merchant in merchants:
            docs.append({
                "text": self._merchant_text(merchant),
                "source_type": "merchant",
                "source_id": merchant["id"],
                "facts": {
                    **merchant,
                    "merchant_id": merchant["id"],
                    "merchant_name": merchant["name"],
                    "is_available": True,
                },
                "citation": merchant.get("description", ""),
            })

        for merchant in merchants:
            for dish in self.catalog_service.list_dishes_by_merchant(merchant["id"]):
                docs.append({
                    "text": self._dish_text(dish),
                    "source_type": "dish",
                    "source_id": dish["id"],
                    "facts": {
                        **dish,
                        "dish_id": dish["id"],
                        "dish_name": dish["name"],
                        "merchant_id": dish["merchant_id"],
                        "merchant_name": merchant["name"],
                        "merchant_rating": float(merchant.get("rating", 0.0)),
                        "is_available": dish.get("is_available", True),
                    },
                    "citation": dish.get("description", ""),
                })

        if not docs:
            self._docs, self._doc_lengths = [], []
            self._tf, self._inverted = [], {}
            self._N, self._avgdl, self._df = 0, 0.0, {}
            self._tokenizer = self._build_tokenizer([])
            self._built = True
            return

        self._docs = docs
        self._tokenizer = self._build_tokenizer(docs)
        doc_tokens = [self._tokenize(d["text"]) for d in docs]
        self._doc_lengths = [len(t) for t in doc_tokens]
        self._N = len(docs)
        self._avgdl = sum(self._doc_lengths) / max(self._N, 1)

        # Precompute DF, TF, and inverted index in a single pass.
        self._df = {}
        self._tf = []
        self._inverted = {}

        for doc_idx, tokens in enumerate(doc_tokens):
            tf_dict: dict[str, int] = {}
            for t in tokens:
                tf_dict[t] = tf_dict.get(t, 0) + 1
            self._tf.append(tf_dict)
            for t in set(tokens):
                self._df[t] = self._df.get(t, 0) + 1
                self._inverted.setdefault(t, []).append(doc_idx)

        self._built = True

    # ── recall ──────────────────────────────────────────────────────

    @traceable(name="sparse_vector_recall")
    def recall(self, plan: RagQueryPlan, limit: int) -> list[RecallCandidate]:
        if not self._built:
            # Guard against concurrent rebuilds: with several RAG sub-queries
            # running in parallel, only the first should build the index.
            with self._build_lock:
                if not self._built:
                    self.build_index()

        if self._N == 0:
            return []

        source_types = set(plan.source_types)
        queries = list(dict.fromkeys(
            q for q in (plan.expansion_queries or [plan.normalized_query]) if q
        ))
        if not queries:
            return []

        # Each query → independent ranked candidate list, then RRF merge.
        num_searches = len(queries)
        per_query = math.ceil(limit / max(num_searches, 1))

        sub_results: list[list[RecallCandidate]] = []
        for query in queries:
            sub_results.append(self._bm25_query(query, source_types, per_query))

        return self._rrf_merge(sub_results, limit)

    def _bm25_query(
        self, query: str, source_types: set[str], top_k: int,
    ) -> list[RecallCandidate]:
        """Score documents matching a single query via inverted index."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        cfg = get_config().rag
        k1, b = cfg.bm25_k1, cfg.bm25_b

        # Collect candidate doc indices from inverted index.
        candidate_docs: set[int] = set()
        for token in query_tokens:
            if token in self._inverted:
                candidate_docs.update(self._inverted[token])

        # Score only candidate documents.
        scored: list[tuple[float, int]] = []
        for doc_idx in candidate_docs:
            if self._docs[doc_idx]["source_type"] not in source_types:
                continue
            score = self._bm25_score(query_tokens, doc_idx, k1, b)
            if score > 0:
                scored.append((score, doc_idx))

        scored.sort(key=lambda item: item[0], reverse=True)

        max_score = scored[0][0] if scored else 0.0
        candidates: list[RecallCandidate] = []
        for rank, (score, doc_idx) in enumerate(scored[:top_k], 1):
            doc = self._docs[doc_idx]
            normalized = score / max_score if max_score > 0 else 0.0
            candidates.append(RecallCandidate(
                stable_key=f"{doc['source_type']}:{doc['source_id']}",
                source_type=doc["source_type"],
                source_id=doc["source_id"],
                route="sparse",
                rank=rank,
                score=normalized,
                facts=dict(doc["facts"]),
                citation=doc["citation"],
            ))
        return candidates

    # ── scoring ─────────────────────────────────────────────────────

    def _bm25_score(
        self, query_tokens: list[str], doc_idx: int,
        k1: float, b: float,
    ) -> float:
        """BM25 with Robertson-Sparck Jones smoothed IDF."""
        doc_len = self._doc_lengths[doc_idx]
        tf_dict = self._tf[doc_idx]
        score = 0.0

        for token in query_tokens:
            df = self._df.get(token, 0)
            if df == 0:
                continue
            idf = math.log((self._N - df + 0.5) / (df + 0.5) + 1.0)
            tf = tf_dict.get(token, 0)
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / self._avgdl)
            score += idf * numerator / denominator

        q_len = len(query_tokens)
        return score / q_len if q_len else 0.0

    @staticmethod
    def _rrf_merge(
        sub_results: list[list[RecallCandidate]], limit: int, k: int = 60,
    ) -> list[RecallCandidate]:
        """RRF merge across per-query sub-results."""
        rrf_scores: dict[str, float] = {}
        best: dict[str, RecallCandidate] = {}

        for candidates in sub_results:
            for c in candidates:
                rrf_scores[c.stable_key] = rrf_scores.get(c.stable_key, 0.0) + 1.0 / (k + c.rank)
                if c.stable_key not in best or c.score > best[c.stable_key].score:
                    best[c.stable_key] = c

        sorted_keys = sorted(rrf_scores, key=lambda key: rrf_scores[key], reverse=True)
        result: list[RecallCandidate] = []
        for rank, key in enumerate(sorted_keys[:limit], 1):
            candidate = best[key]
            candidate.rank = rank
            candidate.score = rrf_scores[key]
            result.append(candidate)
        return result

    # ── tokenizer ───────────────────────────────────────────────────

    @classmethod
    def _build_tokenizer(cls, docs: list[dict]):
        """Create an instance-level jieba tokenizer with domain vocabulary.

        Extracts dish names, merchant names, cuisine types, flavor profiles,
        tags, and ingredients from the loaded docs and registers them so
        jieba keeps compound terms intact (e.g. "宫保鸡丁" as one token).
        """
        if _jieba_module is None:
            return None

        tokenizer = _jieba_module.Tokenizer()
        seen: set[str] = set()

        for doc in docs:
            facts = doc.get("facts", {})
            for key in ("dish_name", "merchant_name", "name",
                        "cuisine_type", "flavor_profile"):
                word = facts.get(key)
                if word and len(word) >= 2 and word not in seen:
                    tokenizer.add_word(word)
                    seen.add(word)
            for list_key in ("tags", "merchant_tags", "ingredients"):
                for word in facts.get(list_key, []):
                    if word and len(word) >= 2 and word not in seen:
                        tokenizer.add_word(word)
                        seen.add(word)

        logger.debug("BM25 tokenizer: added %d domain words", len(seen))
        return tokenizer

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize with jieba (primary) + character unigrams (fallback).

        Character unigrams are appended for every multi-character token so
        that partial or abbreviated queries (e.g. "鸡丁") can still match
        documents containing full compound terms (e.g. "宫保鸡丁").
        """
        if not text:
            return []
        if self._tokenizer is None:
            return self._bigram_tokenize(text)

        jieba_tokens = [w for w in self._tokenizer.lcut(text) if w.strip()]
        result: list[str] = list(jieba_tokens)
        for token in jieba_tokens:
            if len(token) >= 2:
                result.extend(list(token))
        return result

    @staticmethod
    def _bigram_tokenize(text: str) -> list[str]:
        """Fallback tokenizer: character bigrams + unigrams (no jieba)."""
        if not text or len(text) < 2:
            return list(text) if text else []
        bigrams = [text[i : i + 2] for i in range(len(text) - 1)]
        bigrams.extend(list(text))
        return bigrams

    @staticmethod
    def _merchant_text(merchant: dict) -> str:
        parts = [
            str(merchant.get("name", "")),
            str(merchant.get("description", "")),
            str(merchant.get("homepage_category", "")),
            " ".join(merchant.get("merchant_tags", [])),
        ]
        if merchant.get("phone"):
            parts.append(str(merchant["phone"]))
        if merchant.get("detailed_address"):
            parts.append(str(merchant["detailed_address"]))
        elif merchant.get("address"):
            parts.append(str(merchant["address"]))
        return " ".join(filter(None, parts))

    @staticmethod
    def _dish_text(dish: dict) -> str:
        return " ".join(filter(None, [
            str(dish.get("name", "")),
            str(dish.get("description", "")),
            str(dish.get("cuisine_type", "")),
            str(dish.get("flavor_profile", "")),
            " ".join(dish.get("tags", [])),
            " ".join(dish.get("ingredients", [])),
        ]))
