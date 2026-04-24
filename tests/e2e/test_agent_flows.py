from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import MagicMock, patch
from service.agent_core import AgentCore, AgentDecision
from service.assistant_service import AssistantService


class MockSession:
    pass


def test_knowledge_query_does_not_ask_for_clarification():
    """知识查询不应要求澄清（核心修复）"""
    service = AssistantService(MockSession())

    # Inject AgentCore to simulate LLM decision
    service.agent_core._llm = MagicMock()
    service.agent_core._llm.call.return_value = {
        "reasoning": "用户想找卖咖啡的店，属于查询",
        "intent": "knowledge",
        "needs_clarification": False,
        "tool_calls": [{"name": "search_knowledge_base", "parameters": {"query": "咖啡店"}}],
    }

    from api.schemas import AssistantChatRequest
    request = AssistantChatRequest(session_id="test-1", message="推荐几个卖咖啡的店")

    # Patch retriever to return empty list (avoid DB access)
    with patch.object(service.retriever_cls, "retrieve", return_value=[]):
        response = service.chat(request)

    assert response["response_type"] != "clarification"
    assert response["needs_clarification"] is False


def test_recommendation_without_constraints_asks_for_clarification():
    """缺少约束的个性化推荐应要求澄清"""
    service = AssistantService(MockSession())

    service.agent_core._llm = MagicMock()
    service.agent_core._llm.call.return_value = {
        "reasoning": "用户想要推荐但缺少预算和人数",
        "intent": "recommendation",
        "needs_clarification": True,
        "clarification_question": "请告诉我这顿大概几个人吃、预算多少？",
        "tool_calls": [],
    }

    from api.schemas import AssistantChatRequest
    request = AssistantChatRequest(session_id="test-2", message="推荐几个川菜")

    response = service.chat(request)

    assert response["response_type"] == "clarification"
    assert response["needs_clarification"] is True


def test_greeting_returns_directly():
    """问候意图直接返回，不调用工具"""
    service = AssistantService(MockSession())

    service.agent_core._llm = MagicMock()
    service.agent_core._llm.call.return_value = {
        "reasoning": "问候",
        "intent": "greeting",
        "needs_clarification": False,
        "tool_calls": [],
    }

    from api.schemas import AssistantChatRequest
    request = AssistantChatRequest(session_id="test-3", message="你好")

    response = service.chat(request)

    assert response["response_type"] == "greeting"
    assert "智能点餐助手" in response["message"]
