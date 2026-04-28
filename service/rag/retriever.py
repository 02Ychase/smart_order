from __future__ import annotations

from service.agent_runtime.state import AgentPlan
from service.catalog_service import CatalogService
from service.rag.diversifier import diversify
from service.rag.filters import apply_hard_filters
from service.rag.fusion import reciprocal_rank_fusion
from service.rag.models import FusedCandidate, RagEvidence
from service.rag.query_planner import RagQueryPlanner
from service.rag.recall import BusinessRecallRoute, DenseVectorRecallRoute, SqlCatalogRecallRoute
from service.rag.reranker import WeightedReranker


class AdvancedRagRetriever:
    def __init__(self, session=None, recall_routes=None, query_planner=None, reranker=None) -> None:
        catalog_service = CatalogService(session) if session is not None else None
        self.query_planner = query_planner or RagQueryPlanner()
        if recall_routes is not None:
            self.recall_routes = recall_routes
        else:
            self.recall_routes = [DenseVectorRecallRoute()]
            if catalog_service is not None:
                self.recall_routes.extend([
                    SqlCatalogRecallRoute(catalog_service),
                    BusinessRecallRoute(catalog_service),
                ])
        self.reranker = reranker or WeightedReranker()

    def retrieve(self, original_query: str, agent_plan: AgentPlan, memories: list[dict] | None = None, limit: int = 5) -> list[RagEvidence]:
        plan = self.query_planner.plan(original_query, agent_plan, memories or [])
        route_results = [route.recall(plan, limit=50) for route in self.recall_routes]
        fused = reciprocal_rank_fusion(route_results, limit=50)
        filtered = apply_hard_filters(fused, plan)
        ranked = self.reranker.rerank(filtered, original_query=original_query)
        merchant_scoped = bool(plan.must_filters.get("merchant_name"))
        diversified = diversify(ranked, limit=limit, merchant_scoped=merchant_scoped)
        return [self._to_evidence(item) for item in diversified]

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
