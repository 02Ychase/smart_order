from __future__ import annotations

from service.agent_state import EvidencePack
from service.catalog_service import CatalogService
from service.rag_query_rewriter import RagQueryRewriter
from service.rag_reranker import RagReranker
from tools.assistant_vector_store import AssistantVectorStore


CUISINE_ALIASES = {
    "川菜": {"川菜", "川味麻辣"},
    "湘菜": {"湘菜", "川湘"},
    "粤菜": {"粤菜"},
    "轻食": {"轻食"},
    "咖啡甜品": {"咖啡", "甜点", "烘焙", "饮品", "咖啡甜品"},
}


class RagRetriever:
    def __init__(self, session=None, catalog_service=None, vector_store=None) -> None:
        self.catalog_service = catalog_service or CatalogService(session)
        self.vector_store = vector_store or AssistantVectorStore()
        self.rewriter = RagQueryRewriter()
        self.reranker = RagReranker()

    def retrieve(self, message: str, limit: int = 5) -> list[EvidencePack]:
        rewrite = self.rewriter.rewrite(message)
        merchants = self.catalog_service.list_merchants()
        semantic_scores = self._semantic_scores(rewrite.semantic_queries)

        candidates: list[EvidencePack] = []
        if rewrite.source_types == ["merchant"]:
            for merchant in merchants:
                candidates.append(self._merchant_evidence(merchant, semantic_scores))
            return self.reranker.rerank(candidates, limit=limit)

        filters = rewrite.hard_filters
        for merchant in merchants:
            for dish in self.catalog_service.list_dishes_by_merchant(merchant["id"]):
                if not self._passes_filters(dish, filters):
                    continue
                candidates.append(self._dish_evidence(merchant, dish, semantic_scores, filters))

        return self.reranker.rerank(candidates, limit=limit)

    def _semantic_scores(self, semantic_queries: list[str]) -> dict[str, float]:
        scores: dict[str, float] = {}
        if not self.vector_store.is_ready():
            return scores
        for query in semantic_queries:
            for namespace in ("dishes", "merchants"):
                for match in self.vector_store.semantic_search(query, top_k=20, namespace=namespace):
                    scores[match["id"]] = max(scores.get(match["id"], 0.0), float(match.get("score", 0.0)))
        return scores

    def _passes_filters(self, dish: dict, filters: dict) -> bool:
        cuisine_types = filters.get("cuisine_types") or []
        if cuisine_types:
            allowed = set()
            for cuisine in cuisine_types:
                allowed.update(CUISINE_ALIASES.get(cuisine, {cuisine}))
            if dish.get("cuisine_type") not in allowed:
                return False

        exclude_allergens = filters.get("exclude_allergens") or []
        dish_allergens = set(dish.get("allergens") or [])
        if any(allergen in dish_allergens for allergen in exclude_allergens):
            return False

        budget_max = filters.get("budget_max")
        party_size = filters.get("party_size") or 1
        if budget_max is not None and float(dish["price"]) * int(party_size) > float(budget_max):
            return False

        return True

    def _dish_evidence(
        self,
        merchant: dict,
        dish: dict,
        semantic_scores: dict[str, float],
        filters: dict,
    ) -> EvidencePack:
        dish_key = f"dish_{dish['id']}"
        exclude_allergens = filters.get("exclude_allergens") or []
        why = [dish.get("cuisine_type", ""), f"{float(dish['price']):.0f}元"]
        if exclude_allergens:
            why.extend([f"未命中{item}过敏原" for item in exclude_allergens])
        return EvidencePack(
            source_type="dish",
            source_id=dish["id"],
            merchant_id=merchant["id"],
            title=f"{dish['name']}｜{merchant['name']}",
            facts={
                "dish_id": dish["id"],
                "dish_name": dish["name"],
                "merchant_name": merchant["name"],
                "price": float(dish["price"]),
                "cuisine_type": dish.get("cuisine_type", ""),
                "flavor_profile": dish.get("flavor_profile", ""),
                "allergens": list(dish.get("allergens") or []),
                "semantic_score": semantic_scores.get(dish_key, 0.0),
                "keyword_score": 1.0 if dish["name"] in filters.get("original_query", "") else 0.0,
                "merchant_rating": float(merchant.get("rating", 0.0)),
                "is_recommended": bool(dish.get("is_recommended")),
                "constraint_match_score": 1.0,
            },
            why_matched=[item for item in why if item],
            citation=f"{dish.get('cuisine_type', '')}；{dish.get('flavor_profile', '')}；配料为{'、'.join(dish.get('ingredients') or [])}",
        )

    def _merchant_evidence(self, merchant: dict, semantic_scores: dict[str, float]) -> EvidencePack:
        key = f"merchant_{merchant['id']}"
        return EvidencePack(
            source_type="merchant",
            source_id=merchant["id"],
            merchant_id=merchant["id"],
            title=merchant["name"],
            facts={
                "merchant_name": merchant["name"],
                "business_hours": merchant.get("business_hours", ""),
                "delivery_fee": float(merchant.get("delivery_fee", 0.0)),
                "min_order_amount": float(merchant.get("min_order_amount", 0.0)),
                "merchant_rating": float(merchant.get("rating", 0.0)),
                "semantic_score": semantic_scores.get(key, 0.0),
                "keyword_score": 0.5,
                "is_recommended": False,
                "constraint_match_score": 1.0,
            },
            why_matched=list((merchant.get("merchant_tags") or [])[:3]),
            citation=f"{merchant.get('description', '')}；营业时间 {merchant.get('business_hours', '')}",
        )
