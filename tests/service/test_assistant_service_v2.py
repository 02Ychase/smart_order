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
            "message": "测试回复",
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


class DummySession:
    pass


def test_chat_routes_greeting_without_retrieval() -> None:
    graph = StubGraph({"session_id": "", "message": "你好！", "response_type": "greeting",
                       "needs_clarification": False, "clarification_question": None,
                       "extracted_constraints": None, "recommendations": [], "comparisons": [],
                       "citations": [], "suggested_actions": [], "pending_action": None,
                       "executed_actions": [], "undo_available": False})
    service = AssistantService(DummySession())
    service._graph = graph

    response = service.chat(AssistantChatRequest(message="Hi", session_id=None, user_id=1))

    assert response["response_type"] == "greeting"
    assert response["recommendations"] == []
    assert response["comparisons"] == []


def test_chat_routes_knowledge_query_and_returns_evidence() -> None:
    graph = StubGraph({"session_id": "", "message": "找到以下咖啡店", "response_type": "knowledge",
                       "needs_clarification": False, "clarification_question": None,
                       "extracted_constraints": None,
                       "recommendations": [{"source_type": "merchant", "merchant_id": 2,
                                            "merchant_name": "午后豆房", "dish_id": None,
                                            "dish_name": None, "price": None,
                                            "reason": "咖啡甜品"}],
                       "comparisons": [], "citations": [{"source_type": "merchant", "source_id": 2,
                                                         "title": "午后豆房", "snippet": "精品咖啡"}],
                       "suggested_actions": [], "pending_action": None,
                       "executed_actions": [], "undo_available": False})
    service = AssistantService(DummySession())
    service._graph = graph

    response = service.chat(AssistantChatRequest(message="有哪些卖咖啡的店", session_id="session-coffee", user_id=1))

    assert response["response_type"] != "clarification"
    assert response["needs_clarification"] is False


def test_chat_passes_user_id_and_session_to_graph() -> None:
    graph = StubGraph()
    service = AssistantService(DummySession())
    service._graph = graph

    service.chat(AssistantChatRequest(message="推荐湘菜", session_id="s1", user_id=42))

    state = graph.calls[0][0]
    assert state["user_id"] == 42
    assert state["session_id"] == "s1"
    assert graph.calls[0][1]["configurable"]["thread_id"] == "s1"


def test_chat_generates_session_id_when_none_provided() -> None:
    graph = StubGraph()
    service = AssistantService(DummySession())
    service._graph = graph

    response = service.chat(AssistantChatRequest(message="推荐湘菜", session_id=None, user_id=1))

    assert response["session_id"] != ""
    assert len(response["session_id"]) > 0


def test_chat_does_not_ask_clarification_for_recommendation() -> None:
    """LangGraph agent should attempt to answer rather than asking for clarification."""
    graph = StubGraph({"session_id": "", "message": "推荐结果",
                       "response_type": "recommendation",
                       "needs_clarification": False, "clarification_question": None,
                       "extracted_constraints": None, "recommendations": [
                           {"source_type": "dish", "merchant_id": 1, "merchant_name": "兰姨小炒",
                            "dish_id": 11, "dish_name": "鱼香肉丝", "price": 28.0,
                            "reason": "川菜、28元"}
                       ], "comparisons": [], "citations": [],
                       "suggested_actions": [], "pending_action": None,
                       "executed_actions": [], "undo_available": False})
    service = AssistantService(DummySession())
    service._graph = graph

    response = service.chat(AssistantChatRequest(message="推荐几种川菜", session_id=None, user_id=1))

    assert response["response_type"] == "recommendation"
    assert response["needs_clarification"] is False
