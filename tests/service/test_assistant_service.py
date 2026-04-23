from pathlib import Path
import sys
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.assistant_models import AssistantCandidate
from service.assistant_service import AssistantService, build_assistant_health


class DummySession:
    pass


def test_assistant_service_returns_clarification_before_retrieval(monkeypatch) -> None:
    retrieve_called = {"value": False}

    class StubRetriever:
        def __init__(self, session):
            self.session = session

        def retrieve(self, parsed):
            retrieve_called["value"] = True
            return []

    monkeypatch.setattr("service.assistant_service.AssistantRetriever", StubRetriever, raising=False)

    service = AssistantService(DummySession())
    response = service.chat(SimpleNamespace(message="推荐几种川菜", session_id=None))

    assert response["needs_clarification"] is True
    assert retrieve_called["value"] is False


def test_assistant_service_returns_grounded_dish_recommendations(monkeypatch) -> None:
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
                    summary="酸甜微辣，下饭感强，适合两人晚餐",
                    reason_facts=["川菜", "28元", "不含花生"],
                    citation_title="鱼香肉丝｜兰姨小炒",
                    citation_snippet="川菜；酸甜微辣；配料为猪里脊、木耳、胡萝卜、青椒",
                )
            ]

    monkeypatch.setattr("service.assistant_service.AssistantRetriever", StubRetriever, raising=False)

    service = AssistantService(DummySession())
    response = service.chat(
        SimpleNamespace(
            message="推荐几种川菜，2个人吃，100元以内，不要花生",
            session_id="session-1",
        )
    )

    assert response["session_id"] == "session-1"
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
