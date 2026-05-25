from __future__ import annotations

import contextvars
import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from langsmith import traceable

from service.agent_runtime.state import AgentPlan
from service.catalog_service import CatalogService
from service.rag.diversifier import diversify
from service.rag.filters import apply_hard_filters
from service.rag.fusion import reciprocal_rank_fusion
from service.rag.models import FusedCandidate, RagEvidence
from service.rag.tracing import PipelineTrace, RagEvalOptions, TraceItem
from service.rag.query_planner import RagQueryPlanner
from service.rag.recall import BusinessRecallRoute, DenseVectorRecallRoute, SparseVectorRecallRoute, SqlCatalogRecallRoute
from service.rag.reranker import WeightedReranker
from service.rag.cross_encoder import CrossEncoderReranker
from service.config import get_config

logger = logging.getLogger(__name__)

# Minimum candidates RAG should return so the respond-node LLM can
# pick the best match even when the user asks for just one dish.
RAG_EVIDENCE_FLOOR = 3

# ── Module-level shared RAG result cache (thread-safe) ──────────────
_rag_cache: OrderedDict[str, tuple[float, list[dict[str, Any]]]] = OrderedDict()
_rag_cache_lock = threading.Lock()


class AdvancedRagRetriever:
    def __init__(
        self,
        session=None,
        recall_routes=None,
        query_planner=None,
        reranker=None,
        cross_encoder=None,
        session_factory: Callable | None = None,
    ) -> None:
        self._session_factory = session_factory
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

    @traceable(name="rag_retrieve")
    def retrieve(
        self,
        original_query: str,
        agent_plan: AgentPlan,
        memories: list[dict] | None = None,
        limit: int = 5,
        max_limit: int | None = None,
        trace: PipelineTrace | None = None,
        eval_options: RagEvalOptions | None = None,
    ) -> list[RagEvidence]:
        from service.observability import MetricsCollector
        pipeline_start = time.perf_counter()

        collector = MetricsCollector()
        collector.set_metadata("query", original_query)

        cfg = get_config().rag
        effective_max = max_limit if max_limit is not None else cfg.output_limit_max

        plan = self.query_planner.plan(original_query, agent_plan, memories or [])
        output_limit = self._output_limit(plan, default=limit, max_limit=effective_max)

        skip_cache = eval_options.disable_cache if eval_options else False
        cache_key = ""
        if not skip_cache:
            cache_key = self._cache_key(plan, memories, output_limit)
            cached = self._cache_get(cache_key)
            if cached is not None:
                logger.debug("RAG cache hit: key=%s", cache_key[:32])
                if trace is not None:
                    trace.cache_hit = True
                collector.increment("rag.cache_hit")
                collector.emit("rag_retrieve")
                return [self._dict_to_evidence(item) for item in cached]

        # --- Recall ---
        t0 = time.perf_counter()
        recall_with_timings = self._parallel_recall(plan, limit=50)
        parallel_elapsed = (time.perf_counter() - t0) * 1000
        route_results = [r for r, _ in recall_with_timings]
        recall_counts = [len(r) for r in route_results]
        logger.debug("RAG recall: routes=%d, counts=%s, query=%s", len(route_results), recall_counts, plan.normalized_query)

        if trace is not None:
            trace.parallel_recall_total_ms = parallel_elapsed
            for route, (results, route_ms) in zip(self.recall_routes, recall_with_timings):
                route_name = type(route).__name__
                trace.recall_per_route[route_name] = [
                    TraceItem(key=c.stable_key, score=c.score) for c in results
                ]
                trace.recall_per_route_latency_ms[route_name] = route_ms

        # --- Fusion ---
        t0 = time.perf_counter()
        fused = reciprocal_rank_fusion(route_results, limit=50)
        fusion_elapsed = (time.perf_counter() - t0) * 1000
        logger.debug("RAG fusion: %d candidates after RRF", len(fused))

        if trace is not None:
            trace.fusion_latency_ms = fusion_elapsed
            trace.after_fusion = [TraceItem(key=c.stable_key, score=c.final_score) for c in fused]

        # --- Hard filter ---
        t0 = time.perf_counter()
        filtered = apply_hard_filters(fused, plan)
        filter_elapsed = (time.perf_counter() - t0) * 1000
        logger.debug("RAG filter: %d candidates after hard filters (removed %d)", len(filtered), len(fused) - len(filtered))

        if trace is not None:
            trace.filter_latency_ms = filter_elapsed
            trace.after_hard_filter = [TraceItem(key=c.stable_key, score=c.final_score) for c in filtered]

        rerank_query = plan.normalized_query or original_query

        # --- Cross-encoder ---
        skip_ce = eval_options.skip_cross_encoder if eval_options else False
        if not skip_ce and len(filtered) > 3:
            t0 = time.perf_counter()
            filtered = self.cross_encoder.rerank(rerank_query, filtered, top_k=min(20, len(filtered)))
            ce_elapsed = (time.perf_counter() - t0) * 1000
            logger.debug("RAG cross-encoder: %d candidates after reranking", len(filtered))

            if trace is not None:
                trace.cross_encoder_latency_ms = ce_elapsed
                trace.after_cross_encoder = [
                    TraceItem(key=c.stable_key, score=c.cross_encoder_score) for c in filtered
                ]

        # --- Weighted rerank ---
        skip_wr = eval_options.skip_weighted_rerank if eval_options else False
        if not skip_wr:
            t0 = time.perf_counter()
            ranked = self.reranker.rerank(filtered, original_query=rerank_query, query_plan=plan, memories=memories or [])
            wr_elapsed = (time.perf_counter() - t0) * 1000

            if trace is not None:
                trace.weighted_rerank_latency_ms = wr_elapsed
                trace.after_weighted_rerank = [
                    TraceItem(key=c.stable_key, score=c.final_score) for c in ranked
                ]
        else:
            ranked = filtered

        ranked = self._apply_result_ordering(ranked, plan)

        # --- Diversify ---
        merchant_scoped = bool(plan.must_filters.get("merchant_name"))
        t0 = time.perf_counter()
        diversified = diversify(ranked, limit=output_limit, merchant_scoped=merchant_scoped)
        div_elapsed = (time.perf_counter() - t0) * 1000
        logger.debug("RAG diversify: %d candidates after diversity (limit=%d)", len(diversified), output_limit)

        if trace is not None:
            trace.diversify_latency_ms = div_elapsed
            trace.after_diversify = [TraceItem(key=c.stable_key, score=c.final_score) for c in diversified]
            trace.total_latency_ms = (time.perf_counter() - pipeline_start) * 1000

        collector.set_metadata("recall_counts", recall_counts)
        collector.set_metadata("after_fusion", len(fused))
        collector.set_metadata("after_filter", len(filtered))
        collector.set_metadata("final_count", len(diversified))
        collector.emit("rag_retrieve")

        evidence_list = [self._to_evidence(item) for item in diversified]
        if not skip_cache:
            serialized = [self._evidence_to_dict(e) for e in evidence_list]
            self._cache_set(cache_key, serialized)
        return evidence_list

    def _cache_key(self, plan, memories: list[dict] | None = None, output_limit: int = 5) -> str:
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
            # effective output limit (includes caller default + user request + max cap)
            str(output_limit),
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

    @traceable(name="parallel_recall")
    def _parallel_recall(self, plan, limit: int) -> list[tuple[list, float]]:
        cfg = get_config().rag

        if not cfg.parallel_recall or len(self.recall_routes) <= 1:
            return self._sequential_recall(plan, limit)

        max_workers = min(cfg.recall_max_workers, len(self.recall_routes))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for route in self.recall_routes:
                # Each worker gets its own context copy so LangSmith
                # child spans nest correctly under parallel_recall.
                ctx = contextvars.copy_context()
                futures.append(
                    executor.submit(ctx.run, self._run_single_route, route, plan, limit)
                )
            return [f.result() for f in futures]

    def _sequential_recall(self, plan, limit: int) -> list[tuple[list, float]]:
        """Fallback sequential recall (used when parallel_recall=False)."""
        results: list[tuple[list, float]] = []
        for route in self.recall_routes:
            t0 = time.perf_counter()
            try:
                result = route.recall(plan, limit)
                elapsed = (time.perf_counter() - t0) * 1000
                results.append((result, elapsed))
                logger.debug("RAG recall route %s returned %d candidates", route.__class__.__name__, len(result))
            except Exception as e:
                elapsed = (time.perf_counter() - t0) * 1000
                logger.warning("RAG recall route %s failed: %s", route.__class__.__name__, e)
                results.append(([], elapsed))
        return results

    def _run_single_route(self, route, plan, limit: int) -> tuple[list, float]:
        """Execute one recall route in a worker thread.

        If the route declares ``requires_db_session = True`` and a
        *session_factory* is available, a **fresh** SQLAlchemy session is
        created for this thread so that routes never share a session
        concurrently.  The exception is :class:`SparseVectorRecallRoute`
        whose BM25 index, once built, is purely in-memory and safe to
        read across threads.
        """
        needs_own_session = (
            getattr(route, "requires_db_session", False)
            and self._session_factory is not None
        )
        # Sparse route with a pre-built index is purely in-memory; skip
        # session creation to avoid rebuilding the BM25 index every call.
        if needs_own_session and getattr(route, "_built", False):
            needs_own_session = False

        t0 = time.perf_counter()
        if needs_own_session:
            session = self._session_factory()
            try:
                route_instance = route.__class__(CatalogService(session))
                result = route_instance.recall(plan, limit)
                elapsed = (time.perf_counter() - t0) * 1000
                logger.debug("RAG recall route %s returned %d candidates", route.__class__.__name__, len(result))
                return result, elapsed
            except Exception as e:
                elapsed = (time.perf_counter() - t0) * 1000
                logger.warning("RAG recall route %s failed: %s", route.__class__.__name__, e)
                return [], elapsed
            finally:
                session.close()
        else:
            try:
                result = route.recall(plan, limit)
                elapsed = (time.perf_counter() - t0) * 1000
                logger.debug("RAG recall route %s returned %d candidates", route.__class__.__name__, len(result))
                return result, elapsed
            except Exception as e:
                elapsed = (time.perf_counter() - t0) * 1000
                logger.warning("RAG recall route %s failed: %s", route.__class__.__name__, e)
                return [], elapsed

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
    def _output_limit(plan, default: int, max_limit: int = 20) -> int:
        """Resolve the effective output limit.

        * User didn't specify a count → return *default*.
        * User specified a count → honour it, but cap at *max_limit*.
        * Always return at least RAG_EVIDENCE_FLOOR so the respond-node
          LLM has enough candidates to pick the best match from.
        """
        raw_limit = (plan.should_filters or {}).get("limit")
        try:
            parsed = int(raw_limit)
        except (TypeError, ValueError):
            return default
        return max(RAG_EVIDENCE_FLOOR, min(parsed, max_limit))

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
