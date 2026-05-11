from langchain_core.messages import HumanMessage

from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.state import AgentPlan, GraphToolCall


class MultiStepPlanner:
    """Planner that returns a 2-step plan: search then add_to_cart."""
    def __init__(self):
        self.call_count = 0

    def plan(self, message, context):
        self.call_count += 1
        tool_results = context.get("tool_results", [])
        has_evidence = context.get("recent_evidence", [])

        if self.call_count == 1:
            return AgentPlan(
                intent="cart_action",
                normalized_query="宫保鸡丁",
                requires_rag=True,
                tool_calls=[
                    GraphToolCall("recommend_dishes", {"query": "宫保鸡丁"}, False),
                    GraphToolCall("add_to_cart", {"dish_id": 11, "quantity": 1}, True),
                ],
            )
        # Second call: RAG already done, just the action
        return AgentPlan(
            intent="cart_action",
            tool_calls=[
                GraphToolCall("add_to_cart", {"dish_id": 11, "quantity": 1}, True),
            ],
        )


class StubRetriever:
    def retrieve(self, original_query, agent_plan, memories, limit):
        return [
            type("Evidence", (), {
                "source_type": "dish", "source_id": 11, "merchant_id": 1,
                "title": "宫保鸡丁", "facts": {"dish_id": 11, "dish_name": "宫保鸡丁", "price": 28.0, "merchant_name": "川味坊"},
                "why_matched": ["川菜"], "citation": "经典川菜", "score": 0.9,
            })(),
        ]


class StubActionExecutor:
    def __init__(self):
        self.executed = []

    def execute_action(self, plan, state):
        self.executed.append(plan.tool_calls[0].tool_name if plan.tool_calls else "none")
        return {"success": True, "action_id": "act_test123", "message": "已加入购物车", "undo_available": True}

    def undo_last(self, state):
        return {"success": False, "message": "无可撤回操作"}


def test_multistep_search_then_add():
    planner = MultiStepPlanner()
    retriever = StubRetriever()
    executor = StubActionExecutor()

    graph = build_agent_graph(
        planner=planner,
        retriever=retriever,
        action_executor=executor,
        use_llm_response=False,
        max_iterations=5,
    )

    result = graph.invoke({
        "messages": [HumanMessage(content="帮我把宫保鸡丁加到购物车")],
        "session_id": "test_multi",
        "user_id": 1,
        "loaded_user_memories": [],
        "recent_evidence": [],
        "recent_action_ids": [],
        "tool_results": [],
        "iteration_count": 0,
        "max_iterations": 5,
    }, config={"configurable": {"thread_id": "test_multi"}})

    assert result.get("recent_evidence")
    assert result.get("tool_results")
    assert any(r.get("success") for r in result.get("tool_results", []))
