from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.schemas import AssistantChatRequest
from service.assistant_service import AssistantService


class StubGraph:
    def __init__(self, response_payload=None):
        self.calls = []
        self._payload = response_payload or {
            "session_id": "",
            "message": "",
            "response_type": "recommendation",
            "needs_clarification": False,
            "clarification_question": None,
            "extracted_constraints": None,
            "recommendations": [],
            "comparisons": [],
            "citations": [],
            "suggested_actions": [],
            "pending_action": None,
            "executed_actions": [],
            "undo_available": False,
        }

    def invoke(self, state, config):
        self.calls.append((state, config))
        payload = dict(self._payload)
        payload["session_id"] = state["session_id"]
        return {"response_payload": payload}


class MockSession:
    pass


def test_knowledge_query_does_not_ask_for_clarification():
    """知识查询不应要求澄清"""
    graph = StubGraph({"session_id": "", "message": "找到以下咖啡店",
                       "response_type": "knowledge",
                       "needs_clarification": False, "clarification_question": None,
                       "extracted_constraints": None, "recommendations": [],
                       "comparisons": [], "citations": [],
                       "suggested_actions": [], "pending_action": None,
                       "executed_actions": [], "undo_available": False})
    service = AssistantService(MockSession())
    service._graph = graph

    response = service.chat(AssistantChatRequest(session_id="test-1", message="推荐几个卖咖啡的店", user_id=1))

    assert response["response_type"] != "clarification"
    assert response["needs_clarification"] is False


def test_recommendation_without_constraints_answers_directly():
    """缺少预算人数时也应直接给出推荐，不主动追问"""
    graph = StubGraph({"session_id": "", "message": "推荐川菜结果",
                       "response_type": "recommendation",
                       "needs_clarification": False, "clarification_question": None,
                       "extracted_constraints": None,
                       "recommendations": [{"source_type": "dish", "merchant_id": 1,
                                            "merchant_name": "川味轩", "dish_id": 1,
                                            "dish_name": "麻婆豆腐", "price": 25.0,
                                            "reason": "川菜、麻辣"}],
                       "comparisons": [], "citations": [],
                       "suggested_actions": [], "pending_action": None,
                       "executed_actions": [], "undo_available": False})
    service = AssistantService(MockSession())
    service._graph = graph

    response = service.chat(AssistantChatRequest(session_id="test-2", message="推荐几个川菜", user_id=1))

    assert response["response_type"] == "recommendation"
    assert response["needs_clarification"] is False


def test_greeting_returns_directly():
    """问候意图直接返回"""
    graph = StubGraph({"session_id": "", "message": "你好！我是你的智能点餐助手。",
                       "response_type": "greeting",
                       "needs_clarification": False, "clarification_question": None,
                       "extracted_constraints": None, "recommendations": [],
                       "comparisons": [], "citations": [],
                       "suggested_actions": [], "pending_action": None,
                       "executed_actions": [], "undo_available": False})
    service = AssistantService(MockSession())
    service._graph = graph

    response = service.chat(AssistantChatRequest(session_id="test-3", message="你好", user_id=1))

    assert response["response_type"] == "greeting"
    assert "智能点餐助手" in response["message"]
