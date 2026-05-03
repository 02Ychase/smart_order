from service.rag.models import RagQueryPlan
from service.rag.recall import DenseVectorRecallRoute, SqlCatalogRecallRoute


class StubCatalogService:
    def list_merchants(self):
        return [{"id": 1, "name": "兰姨小炒", "rating": 4.7, "merchant_tags": ["湘菜"], "business_hours": "10:00-21:30"}]

    def list_dishes_by_merchant(self, merchant_id):
        return [
            {"id": 11, "merchant_id": 1, "name": "小炒黄牛肉", "price": 42.0, "cuisine_type": "湘菜", "flavor_profile": "鲜辣下饭", "allergens": [], "is_recommended": True, "is_available": True}
        ]

    def list_dishes_filtered(self, cuisine_types=None, flavor_keywords=None, required_keywords=None, forbidden_keywords=None, merchant_id=None, limit=100):
        return [
            {"id": 11, "merchant_id": 1, "name": "小炒黄牛肉", "price": 42.0, "cuisine_type": "湘菜", "flavor_profile": "鲜辣下饭", "allergens": [], "is_recommended": True, "is_available": True, "description": "黄牛肉片现炒"}
        ]

    def list_merchants_filtered(self, cuisine_types=None, required_keywords=None, limit=50):
        return [{"id": 1, "name": "兰姨小炒", "rating": 4.7, "merchant_tags": ["湘菜"], "business_hours": "10:00-21:30", "description": "地道湘菜馆"}]

    def list_recommended_dishes(self, limit=50):
        return [
            {"id": 11, "merchant_id": 1, "name": "小炒黄牛肉", "price": 42.0, "cuisine_type": "湘菜", "flavor_profile": "鲜辣下饭", "allergens": [], "is_recommended": True, "is_available": True, "description": "黄牛肉片现炒"}
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


class StubVectorStore:
    def is_ready(self):
        return True

    def semantic_search(self, query, top_k, namespace):
        return [
            {
                "id": "dish_11",
                "score": 0.9,
                "metadata": {
                    "source_type": "dish",
                    "source_id": 11,
                    "dish_id": 11,
                    "dish_name": "小炒黄牛肉",
                    "cuisine_type": "湘菜",
                },
            }
        ]


def test_dense_recall_defaults_missing_availability_metadata_to_available() -> None:
    plan = RagQueryPlan(
        original_query="湘菜",
        normalized_query="湘菜",
        expansion_queries=["湘菜"],
        source_types=["dish"],
    )

    candidates = DenseVectorRecallRoute(StubVectorStore()).recall(plan, limit=10)

    assert candidates[0].facts["is_available"] is True
