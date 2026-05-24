"""Tests for ReAct compound task enhancements."""

from service.agent_runtime.state import GraphToolCall


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
