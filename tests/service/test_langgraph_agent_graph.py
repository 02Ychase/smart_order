from langchain_core.messages import HumanMessage

from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.state import AgentPlan


class StubPlanner:
    def plan(self, message, context):
        return AgentPlan(
            intent="recommendation",
            normalized_query="辣的湘菜",
            requires_rag=True,
        )


class StubRetriever:
    def retrieve(self, original_query, agent_plan, memories, limit):
        return [
            type(
                "Evidence",
                (),
                {
                    "source_type": "dish",
                    "source_id": 11,
                    "merchant_id": 1,
                    "title": "小炒黄牛肉｜兰姨小炒",
                    "facts": {
                        "dish_id": 11,
                        "dish_name": "小炒黄牛肉",
                        "merchant_name": "兰姨小炒",
                        "price": 42.0,
                    },
                    "why_matched": ["湘菜", "鲜辣下饭"],
                    "citation": "黄牛肉片现炒",
                    "score": 0.9,
                },
            )()
        ]


def test_graph_returns_recommendation_response() -> None:
    graph = build_agent_graph(planner=StubPlanner(), retriever=StubRetriever())

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="帮我推荐几个比较辣的湘菜")],
            "session_id": "s1",
            "user_id": 9,
        },
        config={"configurable": {"thread_id": "s1"}},
    )

    assert result["response_payload"]["response_type"] == "recommendation"
    assert result["response_payload"]["recommendations"][0]["dish_name"] == "小炒黄牛肉"
