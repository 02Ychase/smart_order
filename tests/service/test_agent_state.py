from service.agent_state import (
    AgentDecision,
    EvidencePack,
    PendingAction,
    ToolCall,
    ToolResult,
    AssistantTurnState,
)


def test_tool_result_success_contract() -> None:
    evidence = EvidencePack(
        source_type="dish",
        source_id=11,
        merchant_id=1,
        title="鱼香肉丝｜兰姨小炒",
        facts={"price": 28.0, "cuisine_type": "川味麻辣"},
        why_matched=["匹配川菜"],
        citation="川味麻辣；酸甜微辣",
    )

    result = ToolResult.ok_result(
        tool_name="recommend_dishes",
        data={"count": 1},
        evidence=[evidence],
    )

    assert result.ok is True
    assert result.error is None
    assert result.evidence[0].source_id == 11


def test_tool_result_error_contract() -> None:
    result = ToolResult.error_result(
        tool_name="search_catalog",
        code="AMBIGUOUS_DISH",
        message="找到了多个同名菜品",
        candidates=[{"dish_id": 11}, {"dish_id": 12}],
    )

    assert result.ok is False
    assert result.error.code == "AMBIGUOUS_DISH"
    assert result.error.candidates == [{"dish_id": 11}, {"dish_id": 12}]


def test_pending_action_expires_and_serializes_items() -> None:
    action = PendingAction(
        action_type="cart_add",
        summary="将鱼香肉丝 1 份加入购物车",
        payload={"items": [{"dish_id": 11, "quantity": 1}]},
        requires_user_id=True,
    )

    assert action.action_id.startswith("pa_")
    assert len(action.action_id) == 15
    assert action.action_type == "cart_add"
    assert action.payload["items"][0]["dish_id"] == 11
    assert action.requires_user_id is True


def test_turn_state_tracks_slots_and_pending_action() -> None:
    state = AssistantTurnState(session_id="s1", user_id=1)
    state.slots["budget"] = 100
    state.pending_action = PendingAction(
        action_type="address_save",
        summary="保存地址",
        payload={"label": "家"},
        requires_user_id=True,
    )

    assert state.slots["budget"] == 100
    assert state.pending_action.action_type == "address_save"


def test_agent_decision_contains_tool_plan() -> None:
    decision = AgentDecision(
        intent="mixed_task",
        reasoning_summary="推荐川菜并准备加购",
        tool_plan=[
            ToolCall(
                tool_name="recommend_dishes",
                arguments={"query": "川菜 下饭"},
                requires_confirmation=False,
            )
        ],
        missing_slots=["budget", "party_size"],
        needs_confirmation=False,
    )

    assert decision.intent == "mixed_task"
    assert decision.tool_plan[0].tool_name == "recommend_dishes"
    assert "budget" in decision.missing_slots
