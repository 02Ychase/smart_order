from service.rag.models import RagQueryPlan
from service.rag.recall import SqlCatalogRecallRoute


class StubCatalogService:
    def list_merchants(self):
        return [{"id": 1, "name": "兰姨小炒", "rating": 4.7, "merchant_tags": ["湘菜"], "business_hours": "10:00-21:30"}]

    def list_dishes_by_merchant(self, merchant_id):
        return [
            {"id": 11, "merchant_id": 1, "name": "小炒黄牛肉", "price": 42.0, "cuisine_type": "湘菜", "flavor_profile": "鲜辣下饭", "allergens": [], "is_recommended": True, "is_available": True}
        ]


def test_sql_recall_returns_dish_candidates_for_cuisine_and_flavor() -> None:
    plan = RagQueryPlan(
        original_query="辣的湘菜",
        normalized_query="辣的湘菜",
        should_filters={"cuisine_types": ["湘菜"], "flavor_preferences": ["辣"]},
        source_types=["dish"],
    )

    candidates = SqlCatalogRecallRoute(StubCatalogService()).recall(plan, limit=10)

    assert candidates[0].stable_key == "dish:11"
    assert candidates[0].facts["dish_name"] == "小炒黄牛肉"
    assert candidates[0].route == "sql"
