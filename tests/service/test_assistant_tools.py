from service.agent_state import EvidencePack
from service.tools.catalog_tool import search_catalog_tool
from service.tools.recommendation_tool import recommend_dishes_tool


class StubRagRetriever:
    def retrieve(self, message, limit=5):
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


def test_search_catalog_tool_returns_evidence() -> None:
    result = search_catalog_tool(query="鱼香肉丝", _retriever=StubRagRetriever())

    assert result.ok is True
    assert result.evidence[0].title == "鱼香肉丝｜兰姨小炒"
