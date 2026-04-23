from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.assistant_service import AssistantService


class DummySession:
    pass


def test_chat_routes_greeting_without_retrieval() -> None:
    service = AssistantService(DummySession())
    response = service.chat(SimpleNamespace(message="Hi", session_id=None))

    assert response["response_type"] == "greeting"
    assert response["recommendations"] == []
    assert response["comparisons"] == []


def test_chat_routes_action_intent_without_retrieval() -> None:
    service = AssistantService(DummySession())
    response = service.chat(SimpleNamespace(message="帮我加入购物车", session_id=None))

    assert response["response_type"] == "action_pending"
    assert response["recommendations"] == []


def test_chat_routes_recommendation_with_retrieval_and_evidence(monkeypatch) -> None:
    from service.assistant_models import AssistantCandidate

    class StubRetriever:
        def __init__(self, session):
            self.session = session

        def retrieve(self, parsed):
            return [
                AssistantCandidate(
                    source_type="dish",
                    source_id=11,
                    merchant_id=1,
                    merchant_name="兰姨小炒",
                    dish_id=11,
                    dish_name="鱼香肉丝",
                    price=28.0,
                    score=0.91,
                    summary="酸甜微辣，下饭感强",
                    reason_facts=["川菜", "28元"],
                    citation_title="鱼香肉丝｜兰姨小炒",
                    citation_snippet="川菜；酸甜微辣",
                )
            ]

    monkeypatch.setattr("service.assistant_service.AssistantRetriever", StubRetriever, raising=False)

    service = AssistantService(DummySession())
    response = service.chat(
        SimpleNamespace(
            message="推荐几种川菜，2个人吃，100元以内",
            session_id="session-1",
        )
    )

    assert response["response_type"] == "recommendation"
    assert len(response["recommendations"]) >= 1
    assert response["recommendations"][0]["dish_name"] == "鱼香肉丝"
    assert len(response["citations"]) >= 1


def test_chat_requests_clarification_for_sparse_recommendation() -> None:
    service = AssistantService(DummySession())
    response = service.chat(SimpleNamespace(message="推荐几种川菜", session_id=None))

    assert response["response_type"] == "clarification"
    assert response["recommendations"] == []
    assert "预算" in response["message"] or "几个人" in response["message"]


def test_chat_executes_action_intent_via_agent_loop() -> None:
    service = AssistantService(DummySession())
    llm_response = '{"thought": "用户想加购", "action": "add_to_cart", "action_input": {"user_id": 1, "dish_id": 11, "quantity": 1}}'

    with patch("service.agent_loop.call_llm", return_value=llm_response):
        service.agent_loop.tool_registry.execute = MagicMock(return_value={"success": True, "dish_id": 11, "quantity": 1})
        response = service.chat(
            SimpleNamespace(message="帮我加入购物车", session_id=None, user_id=1)
        )

    assert response["response_type"] == "action_completed"
    assert "tool_result" in response


def test_chat_does_not_clarify_for_knowledge_query_about_coffee_shops(monkeypatch) -> None:
    """知识类查询（如"有哪些卖咖啡的店"）不应要求人数和预算澄清。"""
    from service.assistant_models import AssistantCandidate

    class StubRetriever:
        def __init__(self, session):
            self.session = session

        def retrieve(self, parsed):
            return [
                AssistantCandidate(
                    source_type="merchant",
                    source_id=2,
                    merchant_id=2,
                    merchant_name="午后豆房",
                    dish_id=None,
                    dish_name=None,
                    price=0.0,
                    score=0.88,
                    summary="精品手冲咖啡和法式甜点",
                    reason_facts=["咖啡甜品", "手冲"],
                    citation_title="午后豆房",
                    citation_snippet="咖啡甜品；精品手冲",
                )
            ]

    monkeypatch.setattr("service.assistant_service.AssistantRetriever", StubRetriever, raising=False)

    service = AssistantService(DummySession())
    response = service.chat(
        SimpleNamespace(message="有哪些卖咖啡的店", session_id="session-coffee")
    )

    assert response["response_type"] != "clarification"
    assert response["needs_clarification"] is False
    assert len(response.get("recommendations", [])) >= 1 or len(response.get("comparisons", [])) >= 1 or response["message"] != ""
