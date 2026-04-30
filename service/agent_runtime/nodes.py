from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from service.agent_runtime.planner import ACTION_TOOL_NAMES, RAG_TOOL_NAMES, LangGraphAgentPlanner
from service.rag.retriever import AdvancedRagRetriever


def latest_user_message(state: dict) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def load_memory_node(state: dict, memory_service=None) -> dict:
    user_id = state.get("user_id")
    if user_id is None or memory_service is None:
        return {"loaded_user_memories": []}
    return {"loaded_user_memories": memory_service.list_memories(user_id)}


def memory_writer_node(state: dict, memory_service=None) -> dict:
    user_id = state.get("user_id")
    if user_id is None or memory_service is None:
        return {"saved_memories": []}
    saved = []
    for candidate in state.get("memory_candidates", []):
        if float(candidate.get("confidence", 0.0)) < 0.75:
            continue
        saved.append(
            memory_service.upsert_memory(
                user_id=user_id,
                memory_type=candidate["memory_type"],
                content=candidate["content"],
                confidence=float(candidate["confidence"]),
            )
        )
    return {"saved_memories": saved}


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
    if plan.requires_rag or any(call.tool_name in RAG_TOOL_NAMES for call in plan.tool_calls):
        return "rag"
    if any(call.tool_name in ACTION_TOOL_NAMES for call in plan.tool_calls):
        return "action"
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


class LocalActionExecutor:
    def __init__(self, session=None):
        self.session = session

    @staticmethod
    def _record_value(record, key: str, default=None):
        if isinstance(record, dict):
            return record.get(key, default)
        return getattr(record, key, default)

    def execute_action(self, plan, state):
        from service.action_journal_service import ActionJournalService
        from service.tools.cart_tool import clear_cart_tool

        user_id = state.get("user_id")
        session_id = state.get("session_id")
        call = next(
            (item for item in plan.tool_calls if item.tool_name in ACTION_TOOL_NAMES),
            plan.tool_calls[0],
        )
        if call.tool_name == "cart_clear":
            result = clear_cart_tool(user_id=user_id, session=self.session)
            journal = ActionJournalService(self.session).record_completed_action(
                session_id=session_id,
                user_id=user_id,
                action_type="cart_clear",
                undo_policy=result["undo_policy"],
                before_snapshot=result["before_snapshot"],
                after_snapshot=result["after_snapshot"],
                undo_tool=result["undo_tool"],
                natural_summary=result["natural_summary"],
            )
            action_id = self._record_value(journal, "action_id")
            return {
                "success": True,
                "action_id": action_id,
                "message": result["natural_summary"],
                "undo_available": True,
            }
        return {
            "success": False,
            "message": f"unsupported action tool: {call.tool_name}",
            "undo_available": False,
        }

    def undo_last(self, state):
        from service.action_journal_service import ActionJournalService
        from service.tools.cart_tool import restore_cart_snapshot_tool

        user_id = state.get("user_id")
        journal = ActionJournalService(self.session)
        record = journal.find_last_undoable(user_id)
        if record is None:
            return {"success": False, "message": "没有可撤回的操作"}

        action_type = self._record_value(record, "action_type")
        before_snapshot = self._record_value(record, "before_snapshot", {})
        action_id = self._record_value(record, "action_id")
        if action_type == "cart_clear":
            restore_cart_snapshot_tool(
                user_id=user_id,
                snapshot=before_snapshot,
                session=self.session,
            )
            journal.mark_undone(action_id)
            return {
                "success": True,
                "action_id": action_id,
                "message": "已撤回清空购物车",
            }
        return {"success": False, "message": f"该操作暂不支持撤回: {action_type}"}


def action_node(state: dict, action_executor=None) -> dict:
    executor = action_executor or LocalActionExecutor()
    result = executor.execute_action(state["current_plan"], state)
    recent_ids = list(state.get("recent_action_ids", []))
    if result.get("action_id"):
        recent_ids.append(result["action_id"])
    return {
        "tool_results": [_normalize_tool_result(result, state)],
        "recent_action_ids": recent_ids,
    }


def undo_node(state: dict, action_executor=None) -> dict:
    executor = action_executor or LocalActionExecutor()
    result = executor.undo_last(state)
    return {"tool_results": [_normalize_tool_result(result, state)]}


def _normalize_tool_result(result: dict, state: dict) -> dict:
    plan = state.get("current_plan")
    tool_name = ""
    if plan and plan.tool_calls:
        tool_name = plan.tool_calls[0].tool_name
    data = dict(result.get("data") or {})
    for key in ("action_id", "undo_available"):
        if key in result:
            data[key] = result[key]
    return {
        "type": result.get("type") or tool_name or "unknown",
        "success": bool(result.get("success", False)),
        "message": result.get("message", ""),
        "data": data,
    }


def respond_node(state: dict) -> dict:
    plan = state.get("current_plan")
    evidence = state.get("recent_evidence", [])
    response_type = _external_response_type(plan, state)
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
        elif item.get("source_type") == "merchant":
            merchant_id = item.get("merchant_id") or facts.get("merchant_id") or facts.get("id") or 0
            merchant_name = facts.get("merchant_name") or facts.get("name") or item.get("title") or ""
            recommendations.append(
                {
                    "source_type": "merchant",
                    "merchant_id": merchant_id,
                    "merchant_name": merchant_name,
                    "dish_id": None,
                    "dish_name": None,
                    "price": None,
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

    tool_results = state.get("tool_results", [])
    if recommendations:
        message = "结合商家数据和匹配理由，我推荐：\n" + "\n".join(
            _recommendation_line(index, item)
            for index, item in enumerate(recommendations, start=1)
        )
    elif tool_results:
        message = tool_results[0].get("message", "操作已完成")
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
        "executed_actions": tool_results,
        "undo_available": bool(state.get("recent_action_ids")),
    }
    return {
        "messages": state.get("messages", []) + [AIMessage(content=message)],
        "response_payload": payload,
    }


def _recommendation_line(index: int, item: dict) -> str:
    if item.get("source_type") == "merchant":
        return f"{index}. {item['merchant_name']}"
    return f"{index}. {item['dish_name']}（{item['merchant_name']}）"


def _external_response_type(plan, state: dict) -> str:
    if plan is None:
        return "unsupported"
    if state.get("tool_results") and plan.intent in {
        "cart_action",
        "address_action",
        "preference_action",
        "undo_action",
    }:
        return "action_completed"
    return plan.intent
