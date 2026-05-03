from __future__ import annotations

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
        rank = 1
        dishes = self.catalog_service.list_recommended_dishes(limit=max(limit, 30))
        for dish in dishes:
            candidates.append(
                RecallCandidate(
                    stable_key=f"dish:{dish['id']}",
                    source_type="dish",
                    source_id=dish["id"],
                    route="business",
                    rank=rank,
                    score=0.7,
                    facts={
                        **dish,
                        "dish_id": dish["id"],
                        "dish_name": dish["name"],
                        "merchant_id": dish["merchant_id"],
                        "merchant_name": "",
                        "merchant_rating": 0.0,
                        "is_available": True,
                    },
                    citation=dish.get("description", ""),
                )
            )
            rank += 1
        return candidates[:limit]
