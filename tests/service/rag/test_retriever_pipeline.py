from service.agent_runtime.state import AgentPlan
from service.rag.retriever import AdvancedRagRetriever


class StubRecallRoute:
    def recall(self, plan, limit):
        from service.rag.models import RecallCandidate

        return [
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
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="辣的湘菜",
        requires_rag=True,
        filters={"cuisine_types": ["湘菜"], "flavor_preferences": ["辣"], "budget_max": None, "party_size": None, "exclude_allergens": []},
    )

    assert retriever.retrieve("帮我推荐几个比较辣的湘菜", agent_plan, memories=[], limit=3) == []
