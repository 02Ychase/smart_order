from service.agent_state import AgentDecision, PendingAction, ToolCall, ToolResult
from service.assistant_orchestrator import AssistantOrchestrator
from service.assistant_session_store import InMemoryAssistantSessionStore


class StubPlanner:
    def plan(self, user_message, session_context):
        return AgentDecision(
            intent="address_action",
            tool_plan=[ToolCall(tool_name="parse_address", arguments={"message": user_message})],
            needs_confirmation=True,
        )


class StubRegistry:
    def execute(self, name, params):
        if name == "parse_address":
            return ToolResult.ok_result(
                tool_name="parse_address",
                data={
                    "address": {
                        "label": "家",
                        "contact_name": "张三",
                        "contact_phone": "13800000000",
                        "city": "上海市",
                        "district": "静安区",
                        "detail_address": "南京西路818号",
                        "longitude": 121.45,
                        "latitude": 31.22,
                        "is_default": False,
                    }
                },
            )
        if name == "commit_address_action":
            return {"id": 7, "label": "家"}
        raise AssertionError(name)


def test_address_request_creates_pending_address_action() -> None:
    store = InMemoryAssistantSessionStore()
    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=StubPlanner(),
        tool_registry=StubRegistry(),
    )

    response = orchestrator.chat(
        message="帮我将以下地址加入地址管理：上海市静安区南京西路818号，联系人张三，电话13800000000",
        session_id="s1",
        user_id=1,
    )

    assert response["response_type"] == "confirmation_required"
    assert response["pending_action"]["type"] == "address_save"
    assert store.get_or_create("s1").pending_action.action_type == "address_save"


def test_confirm_address_action_commits_address() -> None:
    store = InMemoryAssistantSessionStore()
    state = store.get_or_create("s1", user_id=1)
    state.pending_action = PendingAction(
        action_type="address_save",
        summary="保存地址",
        payload={"address": {"label": "家"}},
        requires_user_id=True,
    )
    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=StubPlanner(),
        tool_registry=StubRegistry(),
    )

    response = orchestrator.chat(message="确认", session_id="s1", user_id=1)

    assert response["response_type"] == "action_completed"
    assert response["executed_actions"][0]["type"] == "address_save"
