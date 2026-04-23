from service.assistant_models import AssistantCandidate, AssistantParsedQuery
from service.catalog_service import CatalogService
from service.query_refiner import QueryRefiner
from tools.assistant_vector_store import AssistantVectorStore


CUISINE_ALIASES = {
    "川菜": {"川菜", "川味麻辣"},
    "湘菜": {"湘菜"},
    "粤菜": {"粤菜"},
    "轻食": {"轻食"},
    "咖啡甜品": {"咖啡", "甜点", "烘焙", "饮品"},
}


def _matches_cuisine(requested_cuisines: list[str], dish_cuisine: str) -> bool:
    if not requested_cuisines:
        return True

    for cuisine in requested_cuisines:
        if dish_cuisine in CUISINE_ALIASES.get(cuisine, {cuisine}):
            return True
    return False


class AssistantRetriever:
    def __init__(self, session) -> None:
        self.catalog_service = CatalogService(session)
        self.vector_store = AssistantVectorStore()
        self.query_refiner = QueryRefiner()

    def retrieve(self, parsed: AssistantParsedQuery) -> list[AssistantCandidate]:
        # Step 1: Refine user query for vector search
        refined_query = self.query_refiner.refine(parsed.raw_message)

        # Step 2: Get all merchants and dishes from SQL (base set for filtering)
        merchants = self.catalog_service.list_merchants()
        all_dishes_by_merchant: dict[int, list[dict]] = {}
        for merchant in merchants:
            if parsed.query_type == "comparison":
                if parsed.comparison_targets and merchant["name"] not in parsed.comparison_targets:
                    continue
            all_dishes_by_merchant[merchant["id"]] = self.catalog_service.list_dishes_by_merchant(merchant["id"])

        candidates: list[AssistantCandidate] = []

        # Step 3: Vector semantic search (query -> semantic matches)
        semantic_matches: dict[str, dict] = {}
        if self.vector_store.is_ready() and parsed.query_type in ("recommendation", "knowledge", "comparison"):
            vector_results = self.vector_store.semantic_search(refined_query, top_k=20, namespace="dishes")
            for result in vector_results:
                semantic_matches[result["id"]] = {
                    "score": result["score"],
                    "metadata": result.get("metadata", {}),
                }

            # Also search merchants for comparison queries
            if parsed.query_type == "comparison":
                merchant_results = self.vector_store.semantic_search(refined_query, top_k=10, namespace="merchants")
                for result in merchant_results:
                    mid = result["metadata"].get("merchant_id")
                    if mid and mid in [m["id"] for m in merchants]:
                        semantic_matches[result["id"]] = {
                            "score": result["score"],
                            "metadata": result.get("metadata", {}),
                        }

        # Step 4: Build candidates with constraint filtering
        for merchant in merchants:
            if parsed.query_type == "comparison":
                if parsed.comparison_targets and merchant["name"] not in parsed.comparison_targets:
                    continue
                candidates.append(
                    AssistantCandidate(
                        source_type="merchant",
                        source_id=merchant["id"],
                        merchant_id=merchant["id"],
                        merchant_name=merchant["name"],
                        dish_id=None,
                        dish_name=None,
                        price=None,
                        score=float(merchant["rating"]),
                        summary=f"{merchant['business_hours']} 营业，标签包括 {'、'.join(merchant['merchant_tags'])}",
                        reason_facts=list(merchant["merchant_tags"][:3]),
                        citation_title=merchant["name"],
                        citation_snippet=merchant["description"],
                    )
                )
                continue

            dishes = all_dishes_by_merchant.get(merchant["id"], [])
            for dish in dishes:
                # Hard constraint filtering
                if not _matches_cuisine(parsed.cuisine_types, dish["cuisine_type"]):
                    continue
                if parsed.exclude_allergens and any(
                    allergen in dish["allergens"] for allergen in parsed.exclude_allergens
                ):
                    continue

                # Budget filtering: check if price is within budget per person when party_size available
                if parsed.budget_max is not None:
                    check_price = dish["price"] * (parsed.party_size or 1)
                    if check_price > parsed.budget_max:
                        continue

                # Calculate blended score
                base_score = float(merchant["rating"])
                semantic_score = 0.0
                vector_match = semantic_matches.get(f"dish_{dish['id']}")
                if vector_match:
                    semantic_score = vector_match["score"]

                # Blend: 70% business rating, 30% semantic relevance
                blended_score = base_score * 0.7 + semantic_score * 3.0

                allergen_fact = (
                    f"不含{parsed.exclude_allergens[0]}" if parsed.exclude_allergens else "不含显式过敏原"
                )
                candidates.append(
                    AssistantCandidate(
                        source_type="dish",
                        source_id=dish["id"],
                        merchant_id=merchant["id"],
                        merchant_name=merchant["name"],
                        dish_id=dish["id"],
                        dish_name=dish["name"],
                        price=dish["price"],
                        score=blended_score,
                        summary=dish["description"],
                        reason_facts=[dish["cuisine_type"], f"{dish['price']:.0f}元", allergen_fact],
                        citation_title=f"{dish['name']}｜{merchant['name']}",
                        citation_snippet=f"{dish['cuisine_type']}；{dish['flavor_profile']}；配料为{'、'.join(dish['ingredients'])}",
                    )
                )

        # Step 5: Sort by blended score and return top 3
        return sorted(candidates, key=lambda item: item.score, reverse=True)[:3]
