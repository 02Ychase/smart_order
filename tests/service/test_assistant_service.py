from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.schemas import AssistantChatRequest
from service.assistant_service import AssistantService, build_assistant_health


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


class DummySession:
    pass


def test_assistant_service_does_not_clarify_for_recommendation() -> None:
    """LangGraph agent attempts to answer directly, rather than asking for clarification."""
    graph = StubGraph({"session_id": "", "message": "我推荐以下川菜...",
                       "response_type": "recommendation",
                       "needs_clarification": False, "clarification_question": None,
                       "extracted_constraints": None, "recommendations": [],
                       "comparisons": [], "citations": [],
                       "suggested_actions": [], "pending_action": None,
                       "executed_actions": [], "undo_available": False})
    service = AssistantService(DummySession())
    service._graph = graph

    response = service.chat(AssistantChatRequest(message="推荐几种川菜", session_id=None, user_id=1))

    assert response["response_type"] == "recommendation"
    assert response["needs_clarification"] is False


def test_assistant_service_returns_grounded_dish_recommendations() -> None:
    graph = StubGraph({"session_id": "session-1",
                       "message": "推荐结果",
                       "response_type": "recommendation",
                       "needs_clarification": False, "clarification_question": None,
                       "extracted_constraints": None,
                       "recommendations": [
                           {"source_type": "dish", "merchant_id": 1, "merchant_name": "兰姨小炒",
                            "dish_id": 11, "dish_name": "鱼香肉丝", "price": 28.0,
                            "reason": "川菜、28元、不含花生"}
                       ],
                       "comparisons": [], "citations": [
                           {"source_type": "dish", "source_id": 11,
                            "title": "鱼香肉丝｜兰姨小炒",
                            "snippet": "川菜；酸甜微辣"}
                       ],
                       "suggested_actions": [], "pending_action": None,
                       "executed_actions": [], "undo_available": False})
    service = AssistantService(DummySession())
    service._graph = graph

    response = service.chat(
        AssistantChatRequest(
            message="推荐几种川菜，2个人吃，100元以内，不要花生",
            session_id="session-1",
            user_id=1,
        )
    )

    assert response["session_id"] == "session-1"
    assert response["response_type"] == "recommendation"
    assert response["needs_clarification"] is False
    assert response["recommendations"][0]["dish_name"] == "鱼香肉丝"
    assert response["citations"][0]["source_type"] == "dish"


def test_build_assistant_health_reports_degraded_mode_without_vector_keys(monkeypatch) -> None:
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    monkeypatch.setenv("MODEL_NAME", "gpt-5.4")

    assert build_assistant_health() == {
        "status": "ok",
        "llm_ready": True,
        "vector_store_ready": False,
        "degraded_mode": True,
    }
