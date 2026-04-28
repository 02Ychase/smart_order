from langchain_core.messages import HumanMessage

from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.state import AgentPlan, GraphToolCall


class SequencePlanner:
    def __init__(self):
        self.calls = 0

    def plan(self, message, context):
        self.calls += 1
        if self.calls == 1:
            return AgentPlan(
                intent="cart_action",
                tool_calls=[GraphToolCall("cart_clear", {}, True)],
            )
        return AgentPlan(
            intent="undo_action",
            tool_calls=[GraphToolCall("undo_last_action", {}, True)],
        )


class StubActionExecutor:
    def __init__(self):
        self.undone = False

    def execute_action(self, plan, state):
        return {
            "success": True,
            "action_id": "act_1",
            "message": "清空购物车",
            "undo_available": True,
        }

    def undo_last(self, state):
        self.undone = True
        return {"success": True, "action_id": "act_1", "message": "已撤回清空购物车"}


def test_graph_executes_action_then_undo() -> None:
    executor = StubActionExecutor()
    graph = build_agent_graph(planner=SequencePlanner(), action_executor=executor)

    first = graph.invoke(
        {
            "messages": [HumanMessage(content="清空购物车")],
            "session_id": "s1",
            "user_id": 9,
        },
        config={"configurable": {"thread_id": "s1"}},
    )
    second = graph.invoke(
        {
            "messages": [HumanMessage(content="撤回刚才的操作")],
            "session_id": "s1",
            "user_id": 9,
            "recent_action_ids": ["act_1"],
        },
        config={"configurable": {"thread_id": "s1"}},
    )

    assert first["response_payload"]["response_type"] == "action_completed"
    assert first["response_payload"]["undo_available"] is True
    assert first["response_payload"]["executed_actions"][0]["type"] == "cart_clear"
    assert second["response_payload"]["executed_actions"][0]["success"] is True
    assert second["response_payload"]["executed_actions"][0]["type"] == "undo_last_action"
    assert executor.undone is True
