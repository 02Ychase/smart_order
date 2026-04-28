from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph

from service.agent_runtime.nodes import (
    action_node,
    plan_node,
    rag_node,
    respond_node,
    route_after_plan,
    undo_node,
)
from service.agent_runtime.planner import LangGraphAgentPlanner
from service.agent_runtime.state import SmartOrderAgentState
from service.rag.retriever import AdvancedRagRetriever


def build_agent_graph(planner=None, retriever=None, action_executor=None, checkpointer=None):
    planner = planner or LangGraphAgentPlanner()
    retriever = retriever or AdvancedRagRetriever()
    checkpointer = checkpointer or InMemorySaver()

    workflow = StateGraph(SmartOrderAgentState)
    workflow.add_node("plan", lambda state: plan_node(state, planner))
    workflow.add_node("rag", lambda state: rag_node(state, retriever))
    workflow.add_node("action", lambda state: action_node(state, action_executor))
    workflow.add_node("undo", lambda state: undo_node(state, action_executor))
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("plan")
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
    workflow.add_edge("rag", "respond")
    workflow.add_edge("action", "respond")
    workflow.add_edge("undo", "respond")
    workflow.add_edge("respond", END)
    return workflow.compile(checkpointer=checkpointer)
