from service.assistant_models import AssistantCandidate, AssistantParsedQuery
from service.catalog_service import CatalogService
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

    def retrieve(self, parsed: AssistantParsedQuery) -> list[AssistantCandidate]:
        merchants = self.catalog_service.list_merchants()
        candidates: list[AssistantCandidate] = []

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
                        summary=f"{merchant['business_hours']} 营业，标签包括 {'、'.join(merchant['merchant_tags'])}。",
                        reason_facts=list(merchant["merchant_tags"][:3]),
                        citation_title=merchant["name"],
                        citation_snippet=merchant["description"],
                    )
                )
                continue

            dishes = self.catalog_service.list_dishes_by_merchant(merchant["id"])
            for dish in dishes:
                if not _matches_cuisine(parsed.cuisine_types, dish["cuisine_type"]):
                    continue
                if parsed.exclude_allergens and any(allergen in dish["allergens"] for allergen in parsed.exclude_allergens):
                    continue
                if parsed.budget_max is not None and parsed.party_size is not None and dish["price"] * parsed.party_size > parsed.budget_max:
                    continue

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
                        score=float(merchant["rating"]),
                        summary=dish["description"],
                        reason_facts=[dish["cuisine_type"], f"{dish['price']:.0f}元", allergen_fact],
                        citation_title=f"{dish['name']}｜{merchant['name']}",
                        citation_snippet=f"{dish['cuisine_type']}；{dish['flavor_profile']}；配料为{'、'.join(dish['ingredients'])}",
                    )
                )

        semantic_scores = self.vector_store.semantic_scores(
            parsed.raw_message,
            [candidate.__dict__ for candidate in candidates],
        )
        for candidate in candidates:
            candidate.score += semantic_scores.get(candidate.source_id, 0.0)

        return sorted(candidates, key=lambda item: item.score, reverse=True)[:3]
