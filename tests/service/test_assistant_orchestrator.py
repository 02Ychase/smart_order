from service.agent_state import AgentDecision, EvidencePack, PendingAction, ToolCall, ToolResult
from service.assistant_orchestrator import AssistantOrchestrator
from service.assistant_session_store import InMemoryAssistantSessionStore


class StubPlanner:
    def __init__(self, decision):
        self.decision = decision

    def plan(self, user_message, session_context):
        return self.decision


class StubRegistry:
    def __init__(self, result):
        self.result = result
        self.executed = []

    def execute(self, name, params):
        self.executed.append((name, params))
        return self.result


def test_orchestrator_returns_clarification_for_missing_slots() -> None:
    store = InMemoryAssistantSessionStore()
    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=StubPlanner(
            AgentDecision(
                intent="recommendation",
                missing_slots=["budget", "party_size"],
                clarification_question="请告诉我这顿几个人吃、预算多少？",
            )
        ),
    )

    response = orchestrator.chat(message="推荐川菜", session_id=None, user_id=1)

    assert response["response_type"] == "clarification"
    assert "预算" in response["message"]


def test_orchestrator_creates_pending_cart_action_for_mixed_task() -> None:
    evidence = EvidencePack(
        source_type="dish",
        source_id=11,
        merchant_id=1,
        title="鱼香肉丝｜兰姨小炒",
        facts={"dish_id": 11, "dish_name": "鱼香肉丝", "merchant_name": "兰姨小炒", "price": 28.0},
        why_matched=["匹配川菜"],
        citation="川味麻辣",
    )
    result = ToolResult.ok_result(
        tool_name="recommend_dishes",
        data={"cart_candidate_items": [{"dish_id": 11, "quantity": 1}]},
        evidence=[evidence],
    )
    store = InMemoryAssistantSessionStore()
    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=StubPlanner(
            AgentDecision(
                intent="mixed_task",
                tool_plan=[ToolCall(tool_name="recommend_dishes", arguments={"query": "川菜"})],
                needs_confirmation=True,
            )
        ),
        tool_registry=StubRegistry(result),
    )

    response = orchestrator.chat(message="2人100元推荐川菜并加入购物车", session_id="s1", user_id=1)

    assert response["response_type"] == "confirmation_required"
    assert response["pending_action"]["type"] == "cart_add"
    assert store.get_or_create("s1").pending_action is not None


def test_orchestrator_commits_pending_cart_action_on_confirm() -> None:
    store = InMemoryAssistantSessionStore()
    state = store.get_or_create("s1", user_id=1)
    state.pending_action = PendingAction(
        action_type="cart_add",
        summary="加入购物车",
        payload={"items": [{"dish_id": 11, "quantity": 1}]},
        requires_user_id=True,
    )

    class CommitRegistry:
        def execute(self, name, params):
            return {"success": True, "items": [{"dish_id": 11}]}

    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=StubPlanner(AgentDecision(intent="greeting")),
        tool_registry=CommitRegistry(),
    )

    response = orchestrator.chat(message="确认", session_id="s1", user_id=1)

    assert response["response_type"] == "action_completed"
    assert response["executed_actions"][0]["success"] is True
