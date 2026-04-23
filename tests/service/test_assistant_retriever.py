from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.assistant_models import AssistantParsedQuery
from service.assistant_retriever import AssistantRetriever


class DummyVectorStore:
    def semantic_scores(self, query: str, candidates: list[dict]) -> dict[int, float]:
        return {}

    def semantic_search(self, query: str, top_k: int = 5, namespace: str = "") -> list[dict]:
        return []

    def is_ready(self) -> bool:
        return False


class DummyQueryRefiner:
    def refine(self, message: str) -> str:
        return message


class StubCatalogService:
    def list_merchants(self, district: str | None = None) -> list[dict]:
        return [
            {
                'id': 1,
                'name': '兰姨小炒',
                'description': '家常热炒',
                'rating': 4.8,
                'merchant_tags': ['下饭', '现炒'],
                'business_hours': '10:00-21:00',
            },
            {
                'id': 2,
                'name': '午后豆房',
                'description': '豆乳轻食',
                'rating': 4.6,
                'merchant_tags': ['轻盈', '饮品'],
                'business_hours': '09:00-20:00',
            },
        ]

    def list_dishes_by_merchant(self, merchant_id: int) -> list[dict]:
        dishes = {
            1: [
                {
                    'id': 11,
                    'merchant_id': 1,
                    'name': '鱼香肉丝',
                    'description': '酸甜微辣，下饭感强',
                    'price': 28.0,
                    'cuisine_type': '川味麻辣',
                    'flavor_profile': '酸甜微辣',
                    'ingredients': ['猪里脊', '木耳'],
                    'allergens': [],
                }
            ],
            2: [
                {
                    'id': 21,
                    'merchant_id': 2,
                    'name': '豆乳沙拉',
                    'description': '清爽轻食',
                    'price': 26.0,
                    'cuisine_type': '轻食',
                    'flavor_profile': '清爽',
                    'ingredients': ['生菜', '豆乳'],
                    'allergens': ['牛奶'],
                }
            ],
        }
        return dishes.get(merchant_id, [])


class StubRetriever(AssistantRetriever):
    def __init__(self) -> None:
        self.catalog_service = StubCatalogService()
        self.vector_store = DummyVectorStore()
        self.query_refiner = DummyQueryRefiner()


def test_retriever_returns_candidates_for_seed_taxonomy_variant() -> None:
    retriever = StubRetriever()
    parsed = AssistantParsedQuery(
        raw_message='推荐几种川菜，2个人吃，100元以内，不要花生',
        query_type='recommendation',
        cuisine_types=['川菜'],
        budget_max=100.0,
        party_size=2,
        exclude_allergens=['花生'],
    )

    candidates = retriever.retrieve(parsed)

    assert len(candidates) == 1
    assert candidates[0].dish_name == '鱼香肉丝'



def test_retriever_returns_top_merchants_for_generic_comparison_query() -> None:
    retriever = StubRetriever()
    parsed = AssistantParsedQuery(
        raw_message='比较两家商家',
        query_type='comparison',
        comparison_targets=[],
    )

    candidates = retriever.retrieve(parsed)

    assert [candidate.merchant_name for candidate in candidates] == ['兰姨小炒', '午后豆房']
