from service.agent_runtime.state import AgentPlan
from service.rag.retriever import AdvancedRagRetriever


class StubRecallRoute:
    def __init__(self, candidates=None):
        self.candidates = candidates

    def recall(self, plan, limit):
        from service.rag.models import RecallCandidate

        return self.candidates or [
            RecallCandidate(
                stable_key="dish:11",
                source_type="dish",
                source_id=11,
                route="sql",
                rank=1,
                score=1.0,
                facts={"dish_id": 11, "dish_name": "小炒黄牛肉", "merchant_id": 1, "merchant_name": "兰姨小炒", "price": 42.0, "cuisine_type": "湘菜", "flavor_profile": "鲜辣下饭", "allergens": [], "is_available": True, "merchant_rating": 4.7},
                citation="黄牛肉片现炒，芹菜和小米椒提香提辣。",
            )
        ]


def test_retriever_returns_grounded_evidence() -> None:
    retriever = AdvancedRagRetriever(recall_routes=[StubRecallRoute()])
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="辣的湘菜",
        requires_rag=True,
        filters={"cuisine_types": ["湘菜"], "flavor_preferences": ["辣"], "budget_max": None, "party_size": None, "exclude_allergens": []},
    )

    evidence = retriever.retrieve("帮我推荐几个比较辣的湘菜", agent_plan, memories=[], limit=3)

    assert evidence[0].facts["dish_name"] == "小炒黄牛肉"
    assert "湘菜" in evidence[0].why_matched
    assert evidence[0].citation


def test_retriever_without_session_skips_catalog_routes() -> None:
    retriever = AdvancedRagRetriever()

    route_names = [type(route).__name__ for route in retriever.recall_routes]
    assert "SqlCatalogRecallRoute" not in route_names
    assert "BusinessRecallRoute" not in route_names


def test_retriever_applies_price_desc_and_limit_after_recall() -> None:
    from service.rag.models import RecallCandidate

    retriever = AdvancedRagRetriever(
        recall_routes=[
            StubRecallRoute([
                RecallCandidate(
                    stable_key="dish:1",
                    source_type="dish",
                    source_id=1,
                    route="dense",
                    rank=1,
                    score=0.99,
                    facts={"dish_id": 1, "dish_name": "辣椒炒肉", "merchant_id": 1, "merchant_name": "A", "price": 29.0, "cuisine_type": "湘菜", "is_available": True},
                    citation="辣椒炒肉",
                ),
                RecallCandidate(
                    stable_key="dish:2",
                    source_type="dish",
                    source_id=2,
                    route="dense",
                    rank=2,
                    score=0.80,
                    facts={"dish_id": 2, "dish_name": "剁椒鱼块", "merchant_id": 2, "merchant_name": "B", "price": 38.0, "cuisine_type": "湘菜", "is_available": True},
                    citation="剁椒鱼块",
                ),
                RecallCandidate(
                    stable_key="dish:3",
                    source_type="dish",
                    source_id=3,
                    route="dense",
                    rank=3,
                    score=0.95,
                    facts={"dish_id": 3, "dish_name": "外婆菜炒鸡蛋", "merchant_id": 3, "merchant_name": "C", "price": 24.0, "cuisine_type": "湘菜", "is_available": True},
                    citation="外婆菜炒鸡蛋",
                ),
            ])
        ]
    )
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="最贵的湘菜",
        requires_rag=True,
        filters={
            "cuisine_types": ["湘菜"],
            "flavor_preferences": [],
            "budget_max": None,
            "party_size": None,
            "exclude_allergens": [],
            "sort_by": "price_desc",
            "limit": 1,
        },
    )

    evidence = retriever.retrieve("推荐一个最贵的湘菜", agent_plan, memories=[], limit=3)

    assert len(evidence) == 1
    assert evidence[0].facts["dish_name"] == "剁椒鱼块"
