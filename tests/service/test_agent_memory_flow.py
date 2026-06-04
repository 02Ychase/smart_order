from langchain_core.messages import HumanMessage

from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.nodes import (
    load_memory_node,
    memory_writer_node,
    write_memories_for_state,
)
from service.agent_runtime.runtime import AgentRuntimeContext
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


def _make_config(**kwargs):
    """Helper to build a LangGraph config with runtime context for node-level tests."""
    return {"configurable": {"runtime": AgentRuntimeContext(**kwargs)}}


def test_load_memory_node_loads_user_memories() -> None:
    state = {"user_id": 9}
    config = _make_config(memory_service=StubMemoryService())

    result = load_memory_node(state, config)

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
    config = _make_config(memory_service=service)

    memory_writer_node(state, config)

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
    config = _make_config(memory_service=service)

    result = memory_writer_node(state, config)

    assert result["saved_memories"] == []
    assert service.saved == []


class GreetingPlanner:
    def plan(self, message, context):
        return AgentPlan(intent="greeting", should_answer_directly=True)


def test_write_memories_for_state_saves_high_confidence() -> None:
    """Core helper persists high-confidence candidates (used by the
    background worker and memory_writer_node)."""
    service = StubMemoryService()
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

    saved = write_memories_for_state(state, service)

    assert saved[0]["content"] == "prefers spicy Hunan dishes"
    assert service.saved[0]["content"] == "prefers spicy Hunan dishes"


def test_graph_does_not_write_memory_synchronously() -> None:
    """Memory writing was moved off the response graph to a background
    worker, so the graph itself must no longer persist memories inline."""
    service = StubMemoryService()
    graph = build_agent_graph()

    runtime = AgentRuntimeContext(
        planner=GreetingPlanner(),
        memory_service=service,
    )

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
        config={"configurable": {"thread_id": "s1", "runtime": runtime}},
    )

    # Graph terminates at `respond`; it no longer writes memory inline.
    assert not result.get("saved_memories")
    assert service.saved == []


def test_dispatch_memory_write_snapshots_and_submits(monkeypatch) -> None:
    """dispatch_memory_write is fire-and-forget: it snapshots the needed
    fields and hands them to the background executor."""
    from service import assistant_service

    captured: dict = {}
    monkeypatch.setattr(
        assistant_service._memory_executor,
        "submit",
        lambda fn, snap: captured.update(fn=fn, snap=snap),
    )

    assistant_service.dispatch_memory_write(
        {"user_id": 7, "messages": [HumanMessage(content="hi")], "memory_candidates": []}
    )

    assert captured["snap"]["user_id"] == 7
    assert captured["fn"] is assistant_service._run_memory_write


def test_dispatch_memory_write_skips_anonymous_users(monkeypatch) -> None:
    from service import assistant_service

    called = False

    def _fail(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(assistant_service._memory_executor, "submit", _fail)
    assistant_service.dispatch_memory_write({"user_id": None, "messages": []})

    assert called is False
