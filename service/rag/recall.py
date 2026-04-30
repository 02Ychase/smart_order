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

    def recall(self, plan: RagQueryPlan, limit: int) -> list[RecallCandidate]:
        candidates = []
        cuisine_types = set(plan.should_filters.get("cuisine_types") or [])
        flavor_preferences = plan.should_filters.get("flavor_preferences") or []
        source_types = set(plan.source_types)

        rank = 1
        for merchant in self.catalog_service.list_merchants():
            if "merchant" in source_types:
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
            if "dish" not in source_types:
                continue
            for dish in self.catalog_service.list_dishes_by_merchant(merchant["id"]):
                if cuisine_types and dish.get("cuisine_type") not in cuisine_types and merchant.get("homepage_category") not in cuisine_types:
                    continue
                text = " ".join([dish.get("name", ""), dish.get("description", ""), dish.get("flavor_profile", ""), dish.get("cuisine_type", "")])
                if flavor_preferences and not any(pref in text for pref in flavor_preferences):
                    continue
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
                            "merchant_id": merchant["id"],
                            "merchant_name": merchant["name"],
                            "merchant_rating": merchant.get("rating", 0.0),
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
        for merchant in self.catalog_service.list_merchants():
            for dish in self.catalog_service.list_dishes_by_merchant(merchant["id"]):
                if not dish.get("is_recommended"):
                    continue
                candidates.append(
                    RecallCandidate(
                        stable_key=f"dish:{dish['id']}",
                        source_type="dish",
                        source_id=dish["id"],
                        route="business",
                        rank=rank,
                        score=float(merchant.get("rating") or 0.0) / 5.0,
                        facts={**dish, "dish_id": dish["id"], "dish_name": dish["name"], "merchant_id": merchant["id"], "merchant_name": merchant["name"], "merchant_rating": merchant.get("rating", 0.0), "is_available": True},
                        citation=dish.get("description", ""),
                    )
                )
                rank += 1
        return candidates[:limit]
