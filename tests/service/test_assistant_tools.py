from service.agent_state import EvidencePack
from service.rag.models import RagEvidence
from service.tools.catalog_tool import search_catalog_tool
from service.tools.recommendation_tool import recommend_dishes_tool


class StubRagRetriever:
    def __init__(self):
        self.last_message = None

    def retrieve(self, message, limit=5):
        self.last_message = message
        return [
            EvidencePack(
                source_type="dish",
                source_id=11,
                merchant_id=1,
                title="鱼香肉丝｜兰姨小炒",
                facts={
                    "dish_id": 11,
                    "dish_name": "鱼香肉丝",
                    "merchant_name": "兰姨小炒",
                    "price": 28.0,
                },
                why_matched=["匹配川菜"],
                citation="川味麻辣；酸甜微辣",
                score=0.91,
            )
        ]


class PriceSortedStubRagRetriever:
    def retrieve(self, message, limit=5):
        return [
            EvidencePack(
                source_type="dish",
                source_id=21,
                merchant_id=2,
                title="回锅肉｜川湘小馆",
                facts={"dish_id": 21, "dish_name": "回锅肉", "merchant_name": "川湘小馆", "price": 38.0},
                why_matched=["川菜"],
                citation="川味家常；38元",
                score=0.88,
            ),
            EvidencePack(
                source_type="dish",
                source_id=31,
                merchant_id=3,
                title="水煮牛肉｜川湘小馆",
                facts={"dish_id": 31, "dish_name": "水煮牛肉", "merchant_name": "川湘小馆", "price": 88.0},
                why_matched=["川菜"],
                citation="川味麻辣；88元",
                score=0.86,
            ),
        ]


class AdvancedStubRagRetriever:
    def __init__(self):
        self.last_query = None
        self.last_agent_plan = None
        self.last_memories = None
        self.last_limit = None

    def retrieve(self, original_query, agent_plan, memories=None, limit=5):
        self.last_query = original_query
        self.last_agent_plan = agent_plan
        self.last_memories = memories
        self.last_limit = limit
        return [
            RagEvidence(
                source_type="dish",
                source_id=11,
                merchant_id=1,
                title="小炒黄牛肉｜兰姨小炒",
                facts={
                    "dish_id": 11,
                    "dish_name": "小炒黄牛肉",
                    "merchant_name": "兰姨小炒",
                    "price": 42.0,
                    "cuisine_type": "湘菜",
                },
                why_matched=["湘菜", "鲜辣下饭"],
                citation="黄牛肉片现炒，芹菜和小米椒提香提辣。",
                score=0.88,
            )
        ]


def test_recommend_dishes_tool_returns_evidence_and_cart_candidates() -> None:
    result = recommend_dishes_tool(
        query="川菜 下饭",
        budget=100,
        party_size=2,
        exclude_allergens=["花生"],
        _retriever=StubRagRetriever(),
    )

    assert result.ok is True
    assert result.data["cart_candidate_items"] == [{"dish_id": 11, "quantity": 1}]
    assert result.evidence[0].source_id == 11


def test_recommend_dishes_tool_accepts_planner_argument_aliases() -> None:
    retriever = StubRagRetriever()

    result = recommend_dishes_tool(
        query="推荐几个菜",
        cuisine="川菜",
        budget_max=100,
        party_size=3,
        _retriever=retriever,
    )

    assert result.ok is True
    assert "川菜" in retriever.last_message
    assert "100元以内" in retriever.last_message
    assert "3个人" in retriever.last_message


def test_recommend_dishes_tool_builds_query_from_structured_arguments() -> None:
    retriever = StubRagRetriever()

    result = recommend_dishes_tool(
        cuisine="川菜",
        budget_max=100,
        party_size=3,
        _retriever=retriever,
    )

    assert result.ok is True
    assert "川菜" in retriever.last_message
    assert "100元以内" in retriever.last_message


def test_recommend_dishes_tool_prioritizes_price_when_premium_requested() -> None:
    result = recommend_dishes_tool(
        query="川菜 越贵越好",
        premium=True,
        _retriever=PriceSortedStubRagRetriever(),
    )

    assert result.evidence[0].facts["dish_name"] == "水煮牛肉"


def test_recommend_dishes_tool_uses_advanced_retriever_agent_plan() -> None:
    retriever = AdvancedStubRagRetriever()

    result = recommend_dishes_tool(
        query="推荐几个辣的湘菜",
        cuisine="湘菜",
        preferences="辣",
        _retriever=retriever,
        limit=2,
    )

    assert result.ok is True
    assert result.evidence[0].title == "小炒黄牛肉｜兰姨小炒"
    assert retriever.last_agent_plan.intent == "recommendation"
    assert retriever.last_agent_plan.requires_rag is True
    assert retriever.last_agent_plan.filters["cuisine_types"] == ["湘菜"]
    assert retriever.last_agent_plan.filters["flavor_preferences"] == ["辣"]
    assert retriever.last_limit == 2


def test_search_catalog_tool_returns_evidence() -> None:
    result = search_catalog_tool(query="鱼香肉丝", _retriever=StubRagRetriever())

    assert result.ok is True
    assert result.evidence[0].title == "鱼香肉丝｜兰姨小炒"


def test_search_catalog_tool_uses_advanced_retriever_agent_plan() -> None:
    retriever = AdvancedStubRagRetriever()

    result = search_catalog_tool(query="兰姨小炒营业时间", _retriever=retriever, limit=4)

    assert result.ok is True
    assert retriever.last_agent_plan.intent == "knowledge"
    assert retriever.last_agent_plan.requires_rag is True
    assert retriever.last_agent_plan.normalized_query == "兰姨小炒营业时间"
    assert retriever.last_limit == 4
