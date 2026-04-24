import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def assistant_test_context(monkeypatch, tmp_path) -> tuple[TestClient, object]:
    test_database_path = tmp_path / "test_assistant_routes.db"

    monkeypatch.syspath_prepend(str(PROJECT_ROOT))
    monkeypatch.setenv("JWT_SECRET_KEY", "test-phase1-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_database_path.as_posix()}")

    import api.db as api_db
    import api.main as api_main
    import api.routes as api_routes
    import api.routes.assistant as assistant_routes

    importlib.reload(api_db)
    assistant_routes = importlib.reload(assistant_routes)
    importlib.reload(api_routes)
    api_main = importlib.reload(api_main)

    client = TestClient(api_main.app, raise_server_exceptions=False)
    return client, assistant_routes


class StubAssistantService:
    def __init__(self, session):
        self.session = session

    def chat(self, request):
        return {
            "session_id": "session-123",
            "message": "这里有几种川菜推荐",
            "needs_clarification": False,
            "clarification_question": None,
            "extracted_constraints": {
                "query_type": "recommendation",
                "cuisine_types": ["川菜"],
                "budget_max": 50.0,
                "party_size": 2,
                "exclude_allergens": ["花生"],
                "comparison_targets": [],
            },
            "recommendations": [
                {
                    "source_type": "dish",
                    "merchant_id": 11,
                    "merchant_name": "川湘小馆",
                    "dish_id": 101,
                    "dish_name": "宫保鸡丁",
                    "price": 28.0,
                    "reason": "招牌川菜，下饭且接受度高",
                }
            ],
            "comparisons": [
                {
                    "merchant_id": 11,
                    "merchant_name": "川湘小馆",
                    "summary": "适合想吃经典川菜的人群",
                    "highlights": ["招牌热销", "下饭", "口味稳定"],
                }
            ],
            "citations": [
                {
                    "source_type": "merchant",
                    "source_id": 11,
                    "title": "川湘小馆菜单",
                    "snippet": "宫保鸡丁为本店招牌热销菜",
                }
            ],
            "suggested_actions": ["查看商户", "加入购物车"],
        }


def test_assistant_chat_returns_structured_payload(assistant_test_context, monkeypatch) -> None:
    client, assistant_routes = assistant_test_context
    monkeypatch.setattr(assistant_routes, "AssistantService", StubAssistantService)

    response = client.post(
        "/assistant/chat",
        json={"message": "推荐几种川菜", "session_id": None},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session-123"
    assert payload["message"] == "这里有几种川菜推荐"
    assert payload["needs_clarification"] is False
    assert payload["clarification_question"] is None
    assert payload["extracted_constraints"]["query_type"] == "recommendation"
    assert payload["extracted_constraints"]["cuisine_types"] == ["川菜"]
    assert payload["recommendations"][0]["source_type"] == "dish"
    assert payload["recommendations"][0]["dish_name"] == "宫保鸡丁"
    assert payload["comparisons"][0]["merchant_name"] == "川湘小馆"
    assert payload["comparisons"][0]["highlights"] == ["招牌热销", "下饭", "口味稳定"]
    assert payload["citations"][0]["source_id"] == 11
    assert payload["suggested_actions"] == ["查看商户", "加入购物车"]


def test_assistant_chat_can_return_pending_action(assistant_test_context, monkeypatch) -> None:
    client, assistant_routes = assistant_test_context

    class PendingActionAssistantService:
        def __init__(self, session):
            pass

        def chat(self, request):
            return {
                "session_id": request.session_id or "s1",
                "message": "是否加入购物车？",
                "response_type": "confirmation_required",
                "needs_clarification": False,
                "clarification_question": None,
                "extracted_constraints": None,
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": [],
                "pending_action": {
                    "action_id": "pa_1",
                    "type": "cart_add",
                    "summary": "加入 1 道菜",
                    "items": [{"dish_id": 11, "quantity": 1}],
                },
                "executed_actions": [],
            }

    monkeypatch.setattr(assistant_routes, "AssistantService", PendingActionAssistantService)

    response = client.post("/assistant/chat", json={"message": "确认加购"})

    assert response.status_code == 200
    assert response.json()["response_type"] == "confirmation_required"
    assert response.json()["pending_action"]["action_id"] == "pa_1"


def test_assistant_health_reports_dependency_flags(assistant_test_context, monkeypatch) -> None:
    client, assistant_routes = assistant_test_context
    expected_payload = {
        "status": "ok",
        "llm_ready": True,
        "vector_store_ready": False,
        "degraded_mode": True,
    }

    monkeypatch.setattr(assistant_routes, "build_assistant_health", lambda: expected_payload)

    response = client.get("/assistant/health")

    assert response.status_code == 200
    assert response.json() == expected_payload
