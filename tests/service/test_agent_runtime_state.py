from service.agent_runtime.state import AgentPlan, GraphToolCall, SmartOrderAgentState


def test_agent_plan_defaults_answer_directly_for_recommendations() -> None:
    plan = AgentPlan(
        intent="recommendation",
        normalized_query="辣的湘菜",
        requires_rag=True,
    )

    assert plan.should_answer_directly is True
    assert plan.filters["cuisine_types"] == []
    assert plan.tool_calls == []


def test_graph_state_tracks_recent_evidence_and_actions() -> None:
    state = SmartOrderAgentState(
        messages=[],
        session_id="s1",
        user_id=7,
        recent_evidence=[{"source_type": "dish", "source_id": 11}],
        recent_action_ids=["act_1"],
    )

    assert state["session_id"] == "s1"
    assert state["user_id"] == 7
    assert state["recent_evidence"][0]["source_id"] == 11
    assert state["recent_action_ids"] == ["act_1"]


def test_tool_call_records_direct_write_flag() -> None:
    call = GraphToolCall(
        tool_name="cart_clear",
        arguments={"user_id": 7},
        writes_database=True,
    )

    assert call.writes_database is True
