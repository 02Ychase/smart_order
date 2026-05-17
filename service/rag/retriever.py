from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from typing import Any

from service.agent_runtime.state import AgentPlan
from service.catalog_service import CatalogService
from service.rag.diversifier import diversify
from service.rag.filters import apply_hard_filters
from service.rag.fusion import reciprocal_rank_fusion
from service.rag.models import FusedCandidate, RagEvidence
from service.rag.query_planner import RagQueryPlanner
from service.rag.recall import BusinessRecallRoute, DenseVectorRecallRoute, SparseVectorRecallRoute, SqlCatalogRecallRoute
from service.rag.reranker import WeightedReranker
from service.rag.cross_encoder import CrossEncoderReranker
from service.config import get_config

logger = logging.getLogger(__name__)

# ── Module-level shared RAG result cache (thread-safe) ──────────────
_rag_cache: OrderedDict[str, tuple[float, list[dict[str, Any]]]] = OrderedDict()
_rag_cache_lock = threading.Lock()


class AdvancedRagRetriever:
    def __init__(self, session=None, recall_routes=None, query_planner=None, reranker=None, cross_encoder=None) -> None:
        catalog_service = CatalogService(session) if session is not None else None
        self.query_planner = query_planner or RagQueryPlanner()
        if recall_routes is not None:
            self.recall_routes = recall_routes
        else:
            self.recall_routes = [DenseVectorRecallRoute()]
            if catalog_service is not None:
                self.recall_routes.extend([
                    SparseVectorRecallRoute(catalog_service),
                    SqlCatalogRecallRoute(catalog_service),
                    BusinessRecallRoute(catalog_service),
                ])
        self.reranker = reranker or WeightedReranker()
        self.cross_encoder = cross_encoder or CrossEncoderReranker()

    def retrieve(self, original_query: str, agent_plan: AgentPlan, memories: list[dict] | None = None, limit: int = 5) -> list[RagEvidence]:
        from service.observability import MetricsCollector
        collector = MetricsCollector()
        collector.set_metadata("query", original_query)

        plan = self.query_planner.plan(original_query, agent_plan, memories or [])
        cache_key = self._cache_key(plan, memories)
        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.debug("RAG cache hit: key=%s", cache_key[:32])
            collector.increment("rag.cache_hit")
            collector.emit("rag_retrieve")
            return [self._dict_to_evidence(item) for item in cached]

        output_limit = self._output_limit(plan, default=limit)

        with collector.timer("recall"):
            route_results = self._parallel_recall(plan, limit=50)
        recall_counts = [len(r) for r in route_results]
        logger.debug("RAG recall: routes=%d, counts=%s, query=%s", len(route_results), recall_counts, plan.normalized_query)

        with collector.timer("fusion"):
            fused = reciprocal_rank_fusion(route_results, limit=50)
        logger.debug("RAG fusion: %d candidates after RRF", len(fused))

        with collector.timer("filter"):
            filtered = apply_hard_filters(fused, plan)
        logger.debug("RAG filter: %d candidates after hard filters (removed %d)", len(filtered), len(fused) - len(filtered))

        # Cross-encoder reranking (after hard filters, before weighted rerank)
        if len(filtered) > 3:
            filtered = self.cross_encoder.rerank(original_query, filtered, top_k=min(20, len(filtered)))
            logger.debug("RAG cross-encoder: %d candidates after reranking", len(filtered))

        with collector.timer("rerank"):
            ranked = self.reranker.rerank(filtered, original_query=original_query, query_plan=plan, memories=memories or [])
        ranked = self._apply_result_ordering(ranked, plan)

        merchant_scoped = bool(plan.must_filters.get("merchant_name"))
        with collector.timer("diversify"):
            diversified = diversify(ranked, limit=output_limit, merchant_scoped=merchant_scoped)
        logger.debug("RAG diversify: %d candidates after diversity (limit=%d)", len(diversified), output_limit)

        collector.set_metadata("recall_counts", recall_counts)
        collector.set_metadata("after_fusion", len(fused))
        collector.set_metadata("after_filter", len(filtered))
        collector.set_metadata("final_count", len(diversified))
        collector.emit("rag_retrieve")

        evidence_list = [self._to_evidence(item) for item in diversified]
        serialized = [self._evidence_to_dict(e) for e in evidence_list]
        self._cache_set(cache_key, serialized)
        return evidence_list

    def _cache_key(self, plan, memories: list[dict] | None = None) -> str:
        must = plan.must_filters or {}
        should = plan.should_filters or {}
        memory_hash = ""
        if memories:
            memory_contents = sorted([str(m.get("content", "")) for m in memories])
            memory_hash = hashlib.sha256(
                json.dumps(memory_contents, sort_keys=True).encode()
            ).hexdigest()[:16]
        raw = "|".join([
            # query identity
            plan.normalized_query or "",
            plan.original_query or "",
            memory_hash,
            ",".join(sorted(plan.expansion_queries)),
            # structural parameters that change recall / output shape
            ",".join(sorted(plan.source_types)),
            plan.answer_mode or "",
            # must_filters (hard filters)
            ",".join(sorted(must.get("cuisine_types") or [])),
            str(must.get("budget_max") or ""),
            str(must.get("party_size") or ""),
            ",".join(sorted(must.get("exclude_allergens") or [])),
            ",".join(sorted(must.get("required_keywords") or [])),
            ",".join(sorted(must.get("forbidden_keywords") or [])),
            str(must.get("merchant_name") or ""),
            # should_filters (soft filters / ordering)
            ",".join(sorted(should.get("flavor_preferences") or [])),
            str(should.get("limit") or ""),
            str(should.get("sort_by") or ""),
            str(should.get("price_preference") or ""),
            # preference hints
            ",".join(sorted(plan.preferred_dishes)),
            ",".join(sorted(plan.preferred_merchants)),
        ])
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _cache_get(key: str) -> list[dict] | None:
        with _rag_cache_lock:
            entry = _rag_cache.get(key)
            if entry is None:
                return None
            ts, data = entry
            if time.monotonic() - ts > get_config().rag.cache_ttl_seconds:
                del _rag_cache[key]
                return None
            _rag_cache.move_to_end(key)
            return data

    @staticmethod
    def _cache_set(key: str, data: list[dict]) -> None:
        with _rag_cache_lock:
            if key in _rag_cache:
                _rag_cache.move_to_end(key)
            else:
                while len(_rag_cache) >= get_config().rag.cache_max_size:
                    _rag_cache.popitem(last=False)
                _rag_cache[key] = (time.monotonic(), data)

    def _parallel_recall(self, plan, limit: int) -> list[list]:
        results: list[list] = []
        for route in self.recall_routes:
            try:
                result = route.recall(plan, limit)
                results.append(result)
                logger.debug("RAG recall route %s returned %d candidates", route.__class__.__name__, len(result))
            except Exception as e:
                logger.warning("RAG recall route %s failed: %s", route.__class__.__name__, e)
                results.append([])
        return results

    @staticmethod
    def _evidence_to_dict(evidence: RagEvidence) -> dict[str, Any]:
        return {
            "source_type": evidence.source_type,
            "source_id": evidence.source_id,
            "merchant_id": evidence.merchant_id,
            "title": evidence.title,
            "facts": evidence.facts,
            "why_matched": evidence.why_matched,
            "citation": evidence.citation,
            "score": evidence.score,
        }

    @staticmethod
    def _dict_to_evidence(data: dict[str, Any]) -> RagEvidence:
        return RagEvidence(
            source_type=data["source_type"],
            source_id=data["source_id"],
            merchant_id=data["merchant_id"],
            title=data["title"],
            facts=data["facts"],
            why_matched=data.get("why_matched", []),
            citation=data.get("citation", ""),
            score=data.get("score", 0.0),
        )

    @staticmethod
    def _output_limit(plan, default: int) -> int:
        raw_limit = (plan.should_filters or {}).get("limit")
        try:
            parsed = int(raw_limit)
        except (TypeError, ValueError):
            return default
        return max(1, min(parsed, default))

    @staticmethod
    def _apply_result_ordering(candidates: list[FusedCandidate], plan) -> list[FusedCandidate]:
        sort_by = (plan.should_filters or {}).get("sort_by")
        if sort_by == "price_desc":
            return sorted(
                candidates,
                key=lambda item: (
                    float(item.facts.get("price") or 0.0),
                    item.final_score,
                ),
                reverse=True,
            )
        if sort_by == "price_asc":
            return sorted(
                candidates,
                key=lambda item: (
                    float(item.facts.get("price") or 0.0),
                    -item.final_score,
                ),
            )
        return candidates

    def _to_evidence(self, candidate: FusedCandidate) -> RagEvidence:
        facts = candidate.facts
        merchant_id = int(facts.get("merchant_id") or facts.get("id") or 0)
        if candidate.source_type == "dish":
            title = f"{facts.get('dish_name', facts.get('name', '菜品'))}｜{facts.get('merchant_name', '')}"
            why = [
                str(facts.get("cuisine_type", "")),
                str(facts.get("flavor_profile", "")),
                f"{float(facts.get('price', 0.0)):.0f}元" if facts.get("price") is not None else "",
            ]
        else:
            title = str(facts.get("merchant_name") or facts.get("name") or "商家")
            why = [str(item) for item in facts.get("merchant_tags", [])[:3]]

        return RagEvidence(
            source_type=candidate.source_type,
            source_id=candidate.source_id,
            merchant_id=merchant_id,
            title=title,
            facts=facts,
            why_matched=[item for item in why if item],
            citation=candidate.citation,
            score=candidate.final_score,
        )
