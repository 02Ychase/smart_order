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


class SequencePlanner:
    def __init__(self, decisions):
        self.decisions = list(decisions)

    def plan(self, user_message, session_context):
        return self.decisions.pop(0)


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


def test_orchestrator_recommends_premium_cuisine_without_budget_clarification() -> None:
    evidence = EvidencePack(
        source_type="dish",
        source_id=31,
        merchant_id=3,
        title="水煮牛肉｜川湘小馆",
        facts={"dish_id": 31, "dish_name": "水煮牛肉", "merchant_name": "川湘小馆", "price": 88.0},
        why_matched=["川菜", "高价优先"],
        citation="川味麻辣；88元",
    )
    result = ToolResult.ok_result(
        tool_name="recommend_dishes",
        data={"cart_candidate_items": [{"dish_id": 31, "quantity": 1}]},
        evidence=[evidence],
    )
    store = InMemoryAssistantSessionStore()
    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=StubPlanner(
            AgentDecision(
                intent="recommendation",
                missing_slots=["budget", "party_size"],
                clarification_question="请问几个人吃，预算大概多少？",
            )
        ),
        tool_registry=StubRegistry(result),
    )

    response = orchestrator.chat(message="推荐几个比较贵的川菜", session_id="s-premium", user_id=1)

    assert response["response_type"] == "recommendation"
    assert response["recommendations"][0]["dish_name"] == "水煮牛肉"
    assert store.get_or_create("s-premium").slots["cuisine"] == "川菜"
    assert store.get_or_create("s-premium").slots["premium_preference"] is True


def test_orchestrator_uses_recommendation_context_for_short_followups() -> None:
    evidence = EvidencePack(
        source_type="dish",
        source_id=31,
        merchant_id=3,
        title="水煮牛肉｜川湘小馆",
        facts={"dish_id": 31, "dish_name": "水煮牛肉", "merchant_name": "川湘小馆", "price": 88.0},
        why_matched=["川菜", "高价优先"],
        citation="川味麻辣；88元",
    )
    result = ToolResult.ok_result(
        tool_name="recommend_dishes",
        data={"cart_candidate_items": [{"dish_id": 31, "quantity": 1}]},
        evidence=[evidence],
    )
    store = InMemoryAssistantSessionStore()
    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=SequencePlanner(
            [
                AgentDecision(
                    intent="recommendation",
                    missing_slots=["budget", "party_size"],
                    clarification_question="请问几个人吃，预算大概多少？",
                ),
                AgentDecision(intent="unsupported"),
            ]
        ),
        tool_registry=StubRegistry(result),
    )

    first = orchestrator.chat(message="推荐几个比较贵的川菜", session_id="s-follow", user_id=1)
    second = orchestrator.chat(message="无预算上限", session_id="s-follow", user_id=1)

    assert first["response_type"] == "recommendation"
    assert second["response_type"] == "recommendation"
    assert second["recommendations"][0]["dish_name"] == "水煮牛肉"


def test_orchestrator_merges_recommendation_slots_into_planner_tool_call() -> None:
    evidence = EvidencePack(
        source_type="dish",
        source_id=31,
        merchant_id=3,
        title="水煮牛肉｜川湘小馆",
        facts={"dish_id": 31, "dish_name": "水煮牛肉", "merchant_name": "川湘小馆", "price": 88.0},
        why_matched=["川菜", "高价优先"],
        citation="川味麻辣；88元",
    )
    result = ToolResult.ok_result(tool_name="recommend_dishes", evidence=[evidence])
    registry = StubRegistry(result)
    store = InMemoryAssistantSessionStore()
    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=SequencePlanner(
            [
                AgentDecision(
                    intent="recommendation",
                    missing_slots=["budget", "party_size"],
                    clarification_question="请问几个人吃，预算大概多少？",
                ),
                AgentDecision(
                    intent="recommendation",
                    tool_plan=[ToolCall(tool_name="recommend_dishes", arguments={"party_size": 3})],
                ),
            ]
        ),
        tool_registry=registry,
    )

    orchestrator.chat(message="推荐几个比较贵的川菜", session_id="s-merge", user_id=1)
    response = orchestrator.chat(message="3个人", session_id="s-merge", user_id=1)

    assert response["response_type"] == "recommendation"
    assert registry.executed[-1][1]["cuisine"] == "川菜"
    assert registry.executed[-1][1]["premium"] is True


def test_orchestrator_does_not_parse_party_size_as_budget() -> None:
    orchestrator = AssistantOrchestrator(session=None)

    slots = orchestrator._extract_recommendation_slots("3个人")

    assert slots["party_size"] == 3
    assert "budget_max" not in slots
