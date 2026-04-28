from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from service.agent_runtime.planner import LangGraphAgentPlanner
from service.rag.retriever import AdvancedRagRetriever


def latest_user_message(state: dict) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def plan_node(state: dict, planner: LangGraphAgentPlanner) -> dict:
    user_message = latest_user_message(state)
    plan = planner.plan(
        user_message,
        {
            "session_id": state.get("session_id"),
            "user_id": state.get("user_id"),
            "loaded_user_memories": state.get("loaded_user_memories", []),
            "recent_action_ids": state.get("recent_action_ids", []),
        },
    )
    return {"current_plan": plan}


def route_after_plan(state: dict) -> str:
    plan = state.get("current_plan")
    if plan is None:
        return "respond"
    if plan.intent == "undo_action":
        return "undo"
    if plan.tool_calls:
        return "action"
    if plan.requires_rag:
        return "rag"
    return "respond"


def rag_node(state: dict, retriever: AdvancedRagRetriever) -> dict:
    user_message = latest_user_message(state)
    evidence = retriever.retrieve(
        user_message,
        agent_plan=state["current_plan"],
        memories=state.get("loaded_user_memories", []),
        limit=3,
    )
    serialized = [
        {
            "source_type": item.source_type,
            "source_id": item.source_id,
            "merchant_id": item.merchant_id,
            "title": item.title,
            "facts": item.facts,
            "why_matched": item.why_matched,
            "citation": item.citation,
            "score": item.score,
        }
        for item in evidence
    ]
    return {"recent_evidence": serialized}


def action_node(state: dict) -> dict:
    return {"tool_results": [{"success": False, "message": "action node not configured"}]}


def undo_node(state: dict) -> dict:
    return {"tool_results": [{"success": False, "message": "undo node not configured"}]}


def respond_node(state: dict) -> dict:
    plan = state.get("current_plan")
    evidence = state.get("recent_evidence", [])
    response_type = plan.intent if plan else "unsupported"
    recommendations = []
    citations = []
    for item in evidence:
        facts = item.get("facts", {})
        if item.get("source_type") == "dish":
            recommendations.append(
                {
                    "source_type": "dish",
                    "merchant_id": item.get("merchant_id"),
                    "merchant_name": facts.get("merchant_name", ""),
                    "dish_id": facts.get("dish_id"),
                    "dish_name": facts.get("dish_name"),
                    "price": facts.get("price"),
                    "reason": "、".join(item.get("why_matched", [])),
                }
            )
        citations.append(
            {
                "source_type": item.get("source_type"),
                "source_id": item.get("source_id"),
                "title": item.get("title"),
                "snippet": item.get("citation", ""),
            }
        )

    if recommendations:
        message = "结合商家数据和匹配理由，我推荐：\n" + "\n".join(
            f"{index}. {item['dish_name']}（{item['merchant_name']}）"
            for index, item in enumerate(recommendations, start=1)
        )
    elif response_type == "greeting":
        message = "你好！我是你的智能点餐助手。"
    else:
        message = "我没有找到足够匹配的结果，可以换个说法再试。"

    payload = {
        "session_id": state.get("session_id"),
        "message": message,
        "response_type": response_type,
        "needs_clarification": False,
        "clarification_question": None,
        "extracted_constraints": None,
        "recommendations": recommendations,
        "comparisons": [],
        "citations": citations,
        "suggested_actions": [],
        "pending_action": None,
        "executed_actions": state.get("tool_results", []),
        "undo_available": bool(state.get("recent_action_ids")),
    }
    return {
        "messages": state.get("messages", []) + [AIMessage(content=message)],
        "response_payload": payload,
    }
