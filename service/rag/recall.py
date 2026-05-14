from __future__ import annotations

import math

from service.catalog_service import CatalogService
from service.rag.models import RagQueryPlan, RecallCandidate
from tools.assistant_vector_store import AssistantVectorStore


class DenseVectorRecallRoute:
    def __init__(self, vector_store: AssistantVectorStore | None = None) -> None:
        self.vector_store = vector_store or AssistantVectorStore()

    def recall(self, plan: RagQueryPlan, limit: int) -> list[RecallCandidate]:
        if not self.vector_store.is_ready():
            return []

        candidates = []
        rank = 1
        for query in plan.expansion_queries or [plan.normalized_query]:
            for namespace in ("dishes", "merchants"):
                if namespace == "dishes" and "dish" not in plan.source_types:
                    continue
                if namespace == "merchants" and "merchant" not in plan.source_types:
                    continue
                for match in self.vector_store.semantic_search(query, top_k=limit, namespace=namespace):
                    metadata = match.get("metadata", {})
                    facts = dict(metadata)
                    facts.setdefault("is_available", True)
                    source_type = metadata.get("source_type", "dish")
                    source_id = int(metadata.get("source_id") or metadata.get("dish_id") or metadata.get("merchant_id"))
                    candidates.append(
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
                    rank += 1
        return candidates[:limit]


class SqlCatalogRecallRoute:
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
    def __init__(self, catalog_service: CatalogService) -> None:
        self.catalog_service = catalog_service

    def recall(self, plan: RagQueryPlan, limit: int) -> list[RecallCandidate]:
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
    """BM25 sparse-vector recall that activates the reranker's lexical_score weight.

    Indexes dish/merchant names, descriptions, and categories using character
    bigrams (effective for Chinese without a segmenter).  Scores documents with
    the BM25 ranking function.
    """

    _BM25_K1: float = 1.2
    _BM25_B: float = 0.75

    def __init__(self, catalog_service: CatalogService) -> None:
        self.catalog_service = catalog_service
        self._docs: list[dict] = []
        self._doc_tokens: list[list[str]] = []
        self._doc_lengths: list[int] = []
        self._avgdl: float = 0.0 #文档平均长度
        self._df: dict[str, int] = {} #记录每个token的文档频次（在多少个文档中出现过）
        self._N: int = 0
        self._built: bool = False

    # ── index ────────────────────────────────────────────────────────

    def build_index(self) -> None:
        """Build in-memory BM25 index from all catalog data."""
        docs: list[dict] = []

        for merchant in self.catalog_service.list_merchants():
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

        for merchant in self.catalog_service.list_merchants():
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
            self._docs, self._doc_tokens, self._doc_lengths = [], [], []
            self._N, self._avgdl, self._df = 0, 0.0, {}
            self._built = True
            return

        self._docs = docs
        # 对文档进行分词
        self._doc_tokens = [self._tokenize(d["text"]) for d in docs]
        # 计算每个文档的长度（分词后的token数量）
        self._doc_lengths = [len(t) for t in self._doc_tokens]
        self._N = len(docs)
        self._avgdl = sum(self._doc_lengths) / max(self._N, 1)

        self._df = {}
        # 记录每个token的文档频次（在多少个文档中出现过）
        for tokens in self._doc_tokens:
            for token in set(tokens):
                self._df[token] = self._df.get(token, 0) + 1

        self._built = True

    # ── recall ──────────────────────────────────────────────────────

    def recall(self, plan: RagQueryPlan, limit: int) -> list[RecallCandidate]:
        if not self._built:
            self.build_index()

        if self._N == 0:
            return []

        source_types = set(plan.source_types)
        queries = list(plan.expansion_queries) if plan.expansion_queries else [plan.normalized_query]
        if not queries:
            return []


        doc_scores: list[float] = [0.0] * self._N #每个文档的分数，初始为0.0
        doc_tokens_cache = [self._tokenize(q) for q in queries] #所有query分词后的结果

        for query_tokens in doc_tokens_cache:
            if not query_tokens:
                continue
            for doc_idx, doc in enumerate(self._docs):
                if doc["source_type"] not in source_types:
                    continue
                # 多个query只取最高分的那个
                score = self._bm25_score(query_tokens, doc_idx)
                if score > doc_scores[doc_idx]:
                    doc_scores[doc_idx] = score

        max_score = max(doc_scores) if doc_scores else 0.0
        if max_score > 0:
            doc_scores = [s / max_score for s in doc_scores]

        indexed = [(score, idx) for idx, score in enumerate(doc_scores) if score > 0]
        indexed.sort(key=lambda item: item[0], reverse=True)

        candidates: list[RecallCandidate] = []
        for rank, (score, doc_idx) in enumerate(indexed[:limit], 1):
            doc = self._docs[doc_idx]
            candidates.append(RecallCandidate(
                stable_key=f"{doc['source_type']}:{doc['source_id']}",
                source_type=doc["source_type"],
                source_id=doc["source_id"],
                route="sparse",
                rank=rank,
                score=score,
                facts=dict(doc["facts"]),
                citation=doc["citation"],
            ))
        return candidates

    # ── scoring ─────────────────────────────────────────────────────
    # 简单理解：query 里的词，如果在某个菜品文档中出现，并且这个词不是所有文档都有的泛词，那么这个菜品分数更高
    def _bm25_score(self, query_tokens: list[str], doc_idx: int) -> float:
        """BM25 with Robertson-Sparck Jones smoothed IDF."""
        # 获取当前文档的长度和分词结果
        doc_len = self._doc_lengths[doc_idx]
        doc_tokens = self._doc_tokens[doc_idx]
        score = 0.0

        for token in query_tokens:
            # 计算query中的token在所有文档中出现的次数
            df = self._df.get(token, 0)
            if df == 0:
                continue
            # 计算IDF，使用Robertson-Sparck Jones平滑方法，避免极端值
            # 一个词出现的文档越少，它越稀有，IDF 越高，对分数贡献越大。
            idf = math.log((self._N - df + 0.5) / (df + 0.5) + 1.0)
            # 计算TF，当前 query token 在当前文档中出现了多少次。
            tf = doc_tokens.count(token)
            # tf 越大，分数越高；但不会无限增长。
            numerator = tf * (self._BM25_K1 + 1)
            denominator = tf + self._BM25_K1 * (1 - self._BM25_B + self._BM25_B * doc_len / self._avgdl)
            score += idf * numerator / denominator

        q_len = len(query_tokens)
        return score / q_len if q_len else 0.0

    # ── helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Character bigrams — suitable for Chinese without a segmenter."""
        if not text or len(text) < 2:
            return list(text) if text else []
        bigrams = [text[i : i + 2] for i in range(len(text) - 1)]
        bigrams.extend(list(text))  # unigrams catch single-character queries
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
