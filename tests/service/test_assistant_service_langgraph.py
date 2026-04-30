from api.schemas import AssistantChatRequest
from service.assistant_service import AssistantService


class StubGraph:
    def __init__(self):
        self.calls = []

    def invoke(self, state, config):
        self.calls.append((state, config))
        return {
            "response_payload": {
                "session_id": state["session_id"],
                "message": "推荐结果",
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
        }


def test_assistant_service_invokes_langgraph_runtime() -> None:
    graph = StubGraph()
    service = AssistantService(session=None)
    service._graph = graph

    response = service.chat(
        AssistantChatRequest(message="推荐几个湘菜", session_id="s1", user_id=9)
    )

    assert response["message"] == "推荐结果"
    assert graph.calls[0][1]["configurable"]["thread_id"] == "s1"


def test_assistant_service_builds_graph_with_session_backed_rag_retriever(monkeypatch) -> None:
    captured = {}

    class StubSqlAlchemySession:
        def scalars(self, statement):
            return []

    def fake_build_agent_graph(**kwargs):
        captured.update(kwargs)
        return StubGraph()

    monkeypatch.setattr("service.assistant_service.build_agent_graph", fake_build_agent_graph)
    service = AssistantService(session=StubSqlAlchemySession())

    service.chat(AssistantChatRequest(message="推荐几个湘菜", session_id="s1", user_id=9))

    route_names = [type(route).__name__ for route in captured["retriever"].recall_routes]
    assert "SqlCatalogRecallRoute" in route_names
    assert "BusinessRecallRoute" in route_names
