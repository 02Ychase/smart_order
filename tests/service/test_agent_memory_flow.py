from langchain_core.messages import HumanMessage

from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.nodes import load_memory_node, memory_writer_node
from service.agent_runtime.state import AgentPlan


class StubMemoryService:
    def __init__(self):
        self.saved = []

    def list_memories(self, user_id):
        return [
            {
                "memory_type": "food_preference",
                "content": "prefers spicy Hunan dishes",
                "confidence": 0.9,
            }
        ]

    def upsert_memory(self, user_id, memory_type, content, confidence):
        self.saved.append(
            {
                "user_id": user_id,
                "memory_type": memory_type,
                "content": content,
                "confidence": confidence,
            }
        )
        return self.saved[-1]


def test_load_memory_node_loads_user_memories() -> None:
    state = {"user_id": 9}

    result = load_memory_node(state, memory_service=StubMemoryService())

    assert result["loaded_user_memories"][0]["content"] == "prefers spicy Hunan dishes"


def test_memory_writer_saves_high_confidence_memory_candidates() -> None:
    state = {
        "user_id": 9,
        "memory_candidates": [
            {
                "memory_type": "food_preference",
                "content": "prefers spicy Hunan dishes",
                "confidence": 0.9,
            }
        ],
    }
    service = StubMemoryService()

    memory_writer_node(state, memory_service=service)

    assert service.saved[0]["content"] == "prefers spicy Hunan dishes"


def test_memory_writer_skips_low_confidence_candidates() -> None:
    state = {
        "user_id": 9,
        "memory_candidates": [
            {
                "memory_type": "food_preference",
                "content": "maybe likes spicy food",
                "confidence": 0.5,
            }
        ],
    }
    service = StubMemoryService()

    result = memory_writer_node(state, memory_service=service)

    assert result["saved_memories"] == []
    assert service.saved == []


class GreetingPlanner:
    def plan(self, message, context):
        return AgentPlan(intent="greeting", should_answer_directly=True)


def test_graph_writes_memory_candidates_after_response() -> None:
    service = StubMemoryService()
    graph = build_agent_graph(planner=GreetingPlanner(), memory_service=service)

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="你好")],
            "session_id": "s1",
            "user_id": 9,
            "memory_candidates": [
                {
                    "memory_type": "food_preference",
                    "content": "prefers spicy Hunan dishes",
                    "confidence": 0.9,
                }
            ],
        },
        config={"configurable": {"thread_id": "s1"}},
    )

    assert result["saved_memories"][0]["content"] == "prefers spicy Hunan dishes"
    assert service.saved[0]["content"] == "prefers spicy Hunan dishes"
