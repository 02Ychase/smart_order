from __future__ import annotations

import threading

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph

from service.agent_runtime.nodes import (
    action_node,
    evaluate_node,
    input_guardrail_node,
    load_memory_node,
    memory_writer_node,
    plan_node,
    rag_node,
    respond_node,
    route_after_evaluate,
    route_after_plan,
    undo_node,
)
from service.agent_runtime.state import SmartOrderAgentState

# ── Cached compiled graph (module-level singleton) ──────────────────
_compiled_graph = None
_graph_lock = threading.Lock()


def get_agent_graph():
    """Return the cached compiled agent graph singleton.

    The production graph is compiled **without** a checkpointer so that
    per-session checkpoint data does not accumulate in process memory.
    Conversation history is managed externally by InMemoryConversationStore.

    Per-request services are injected via ``config["configurable"]["runtime"]``.
    """
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph
    with _graph_lock:
        if _compiled_graph is None:
            _compiled_graph = _build_graph(checkpointer=None)
    return _compiled_graph


def build_agent_graph(checkpointer=None):
    """Build a fresh (non-cached) agent graph.

    Intended for tests that need an isolated graph instance per test case.
    Defaults to ``InMemorySaver`` so that multi-turn test scenarios work
    out of the box.  Production code should use :func:`get_agent_graph`.
    """
    if checkpointer is None:
        checkpointer = InMemorySaver()
    return _build_graph(checkpointer=checkpointer)


def _build_graph(checkpointer=None):

    workflow = StateGraph(SmartOrderAgentState)

    # All nodes read runtime services from config, no lambdas needed
    workflow.add_node("input_guardrail", input_guardrail_node)
    workflow.add_node("load_memory", load_memory_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("action", action_node)
    workflow.add_node("undo", undo_node)
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("respond", respond_node)
    workflow.add_node("write_memory", memory_writer_node)

    workflow.set_entry_point("input_guardrail")
    workflow.add_conditional_edges(
        "input_guardrail",
        lambda state: "respond" if state.get("guardrail_blocked") else "load_memory",
        {"respond": "respond", "load_memory": "load_memory"},
    )
    workflow.add_edge("load_memory", "plan")
    workflow.add_conditional_edges(
        "plan",
        route_after_plan,
        {
            "rag": "rag",
            "action": "action",
            "undo": "undo",
            "respond": "respond",
        },
    )

    workflow.add_edge("rag", "evaluate")
    workflow.add_edge("action", "evaluate")
    workflow.add_edge("undo", "evaluate")

    workflow.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "plan": "plan",
            "respond": "respond",
        },
    )

    workflow.add_edge("respond", "write_memory")
    workflow.add_edge("write_memory", END)

    if checkpointer is not None:
        return workflow.compile(checkpointer=checkpointer)
    return workflow.compile()
