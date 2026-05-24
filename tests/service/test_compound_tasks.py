"""Tests for ReAct compound task enhancements."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import HumanMessage

from service.agent_runtime.nodes import _normalize_tool_result, plan_node
from service.agent_runtime.planner import LangGraphAgentPlanner
from service.agent_runtime.state import AgentPlan, GraphToolCall


def test_graph_tool_call_has_step_id_field():
    call = GraphToolCall(tool_name="add_to_cart", arguments={"dish_id": 1}, writes_database=True)
    assert hasattr(call, "step_id")
    assert call.step_id == ""


def test_graph_tool_call_step_id_can_be_set():
    call = GraphToolCall(
        tool_name="add_to_cart",
        arguments={"dish_id": 1},
        writes_database=True,
        step_id="add_to_cart_0",
    )
    assert call.step_id == "add_to_cart_0"


def test_parse_tool_calls_generates_unique_step_ids():
    """Same tool_name with different arguments must NOT be deduplicated."""
    planner = LangGraphAgentPlanner()
    raw_calls = [
        {"tool_name": "add_to_cart", "arguments": {"dish_id": 12, "quantity": 1}, "writes_database": True},
        {"tool_name": "add_to_cart", "arguments": {"dish_id": 35, "quantity": 1}, "writes_database": True},
        {"tool_name": "add_to_cart", "arguments": {"dish_id": 7, "quantity": 1}, "writes_database": True},
    ]
    calls = planner._parse_tool_calls(raw_calls, "cart_action")
    assert len(calls) == 3
    step_ids = [c.step_id for c in calls]
    assert step_ids == ["add_to_cart_0", "add_to_cart_1", "add_to_cart_2"]
    assert calls[0].arguments["dish_id"] == 12
    assert calls[1].arguments["dish_id"] == 35
    assert calls[2].arguments["dish_id"] == 7


def test_parse_tool_calls_deduplicates_by_step_id():
    """Calls with the same explicit step_id should be deduplicated."""
    planner = LangGraphAgentPlanner()
    raw_calls = [
        {"tool_name": "add_to_cart", "arguments": {"dish_id": 12}, "writes_database": True, "step_id": "add_to_cart_0"},
        {"tool_name": "add_to_cart", "arguments": {"dish_id": 12}, "writes_database": True, "step_id": "add_to_cart_0"},
    ]
    calls = planner._parse_tool_calls(raw_calls, "cart_action")
    assert len(calls) == 1


def test_parse_tool_calls_preserves_llm_step_id():
    """If the LLM provides a step_id, it should be preserved."""
    planner = LangGraphAgentPlanner()
    raw_calls = [
        {"tool_name": "recommend_dishes", "arguments": {"query": "川菜"}, "writes_database": False, "step_id": "rag_sichuan"},
    ]
    calls = planner._parse_tool_calls(raw_calls, "recommendation")
    assert calls[0].step_id == "rag_sichuan"


def test_normalize_tool_result_includes_step_id():
    result = {"success": True, "message": "done", "data": {}}
    state = {"current_plan": None}
    normalized = _normalize_tool_result(result, state, executed_tool_name="add_to_cart", step_id="add_to_cart_0")
    assert normalized["step_id"] == "add_to_cart_0"
    assert normalized["type"] == "add_to_cart"


def test_completed_tools_by_step_id_not_tool_name():
    """Two add_to_cart calls: completing step_id=add_to_cart_0 should NOT mark add_to_cart_1 as done."""
    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[
            GraphToolCall("add_to_cart", {"dish_id": 12}, True, step_id="add_to_cart_0"),
            GraphToolCall("add_to_cart", {"dish_id": 35}, True, step_id="add_to_cart_1"),
        ],
    )
    tool_results = [
        {"type": "add_to_cart", "step_id": "add_to_cart_0", "success": True, "message": "done", "data": {}},
    ]
    completed_step_ids = {r.get("step_id") or r.get("type", "") for r in tool_results}
    remaining = [c for c in plan.tool_calls if c.step_id not in completed_step_ids]
    assert len(remaining) == 1
    assert remaining[0].step_id == "add_to_cart_1"
    assert remaining[0].arguments["dish_id"] == 35


def test_plan_reuse_on_pending_calls():
    """When current plan has pending (not-yet-completed) calls, plan_node should reuse it."""
    original_plan = AgentPlan(
        intent="cart_action",
        tool_calls=[
            GraphToolCall("add_to_cart", {"dish_id": 12}, True, step_id="add_to_cart_0"),
            GraphToolCall("add_to_cart", {"dish_id": 35}, True, step_id="add_to_cart_1"),
        ],
    )
    state = {
        "messages": [HumanMessage(content="把川菜都加入购物车")],
        "current_plan": original_plan,
        "tool_results": [
            {"type": "add_to_cart", "step_id": "add_to_cart_0", "success": True, "message": "done", "data": {}},
        ],
        "session_id": "s1",
        "user_id": 1,
        "loaded_user_memories": [],
        "recent_action_ids": [],
        "iteration_count": 0,
        "recent_evidence": [],
        "last_recommendations": [],
    }

    mock_planner = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.planner = mock_planner

    with patch("service.agent_runtime.nodes.get_runtime", return_value=mock_runtime):
        result = plan_node(state)

    assert result["current_plan"] is original_plan
    mock_planner.plan.assert_not_called()


def test_plan_replan_when_all_calls_completed():
    """When all calls are completed, plan_node should call LLM for re-planning."""
    original_plan = AgentPlan(
        intent="recommendation",
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜"}, False, step_id="recommend_dishes_0"),
        ],
    )
    state = {
        "messages": [HumanMessage(content="推荐几个川菜然后加入购物车")],
        "current_plan": original_plan,
        "tool_results": [
            {"type": "recommend_dishes", "step_id": "recommend_dishes_0", "success": True, "message": "done", "data": {}},
        ],
        "session_id": "s1",
        "user_id": 1,
        "loaded_user_memories": [],
        "recent_action_ids": [],
        "iteration_count": 1,
        "recent_evidence": [{"source_type": "dish", "facts": {"dish_id": 12}}],
        "last_recommendations": [],
    }

    new_plan = AgentPlan(
        intent="cart_action",
        tool_calls=[GraphToolCall("add_to_cart", {"dish_id": 12}, True, step_id="add_to_cart_0")],
    )
    mock_planner = MagicMock()
    mock_planner.plan.return_value = new_plan
    mock_runtime = MagicMock()
    mock_runtime.planner = mock_planner

    with patch("service.agent_runtime.nodes.get_runtime", return_value=mock_runtime):
        result = plan_node(state)

    assert result["current_plan"] is new_plan
    mock_planner.plan.assert_called_once()


def test_replan_deconflicts_step_ids():
    """When re-planning, new step_ids must not collide with already-completed ones."""
    original_plan = AgentPlan(
        intent="recommendation",
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜"}, False, step_id="recommend_dishes_0"),
        ],
    )
    state = {
        "messages": [HumanMessage(content="推荐一个川菜，再推荐一个湘菜")],
        "current_plan": original_plan,
        "tool_results": [
            {"type": "recommend_dishes", "step_id": "recommend_dishes_0", "success": True, "message": "done", "data": {}},
        ],
        "session_id": "s1",
        "user_id": 1,
        "loaded_user_memories": [],
        "recent_action_ids": [],
        "iteration_count": 1,
        "recent_evidence": [{"source_type": "dish", "source_id": 12, "facts": {"dish_id": 12, "cuisine_type": "川菜"}}],
        "last_recommendations": [],
    }

    # LLM returns a new plan with step_id that WOULD collide (recommend_dishes_0)
    colliding_plan = AgentPlan(
        intent="recommendation",
        requires_rag=True,
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "湘菜", "cuisine_types": ["湘菜"]}, False, step_id="recommend_dishes_0"),
        ],
    )
    mock_planner = MagicMock()
    mock_planner.plan.return_value = colliding_plan
    mock_runtime = MagicMock()
    mock_runtime.planner = mock_planner

    with patch("service.agent_runtime.nodes.get_runtime", return_value=mock_runtime):
        result = plan_node(state)

    returned_plan = result["current_plan"]
    # step_id should have been reassigned to avoid collision
    assert returned_plan.tool_calls[0].step_id != "recommend_dishes_0"
    assert returned_plan.tool_calls[0].step_id == "recommend_dishes_1"


def test_build_human_input_injects_evidence():
    context = {
        "recent_evidence": [
            {
                "source_type": "dish",
                "facts": {"dish_id": 12, "dish_name": "宫保鸡丁", "merchant_name": "川味坊", "price": 28.0, "cuisine_type": "川菜", "flavor_profile": "麻辣"},
            },
        ],
        "tool_results": [],
    }
    result = LangGraphAgentPlanner._build_human_input("加入购物车", context)
    assert "## 本轮已检索到的结果" in result
    assert "宫保鸡丁" in result
    assert "dish_id=12" in result


def test_build_human_input_injects_tool_results():
    context = {
        "recent_evidence": [],
        "tool_results": [
            {"type": "add_to_cart", "step_id": "add_to_cart_0", "success": True, "message": "已将宫保鸡丁加入购物车"},
        ],
    }
    result = LangGraphAgentPlanner._build_human_input("还有吗", context)
    assert "## 本轮已完成的操作" in result
    assert "add_to_cart_0" in result
    assert "成功" in result


def test_build_human_input_no_injection_when_empty():
    context = {"recent_evidence": [], "tool_results": []}
    result = LangGraphAgentPlanner._build_human_input("推荐几个川菜", context)
    assert "## 本轮已检索到的结果" not in result
    assert "## 本轮已完成的操作" not in result
    assert "推荐几个川菜" in result
