from __future__ import annotations

import json
import logging

from langchain_core.messages import AIMessage, HumanMessage

from service.agent_runtime.planner import ACTION_TOOL_NAMES, RAG_TOOL_NAMES, LangGraphAgentPlanner
from service.rag.retriever import AdvancedRagRetriever

logger = logging.getLogger(__name__)


def latest_user_message(state: dict) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def input_guardrail_node(state: dict) -> dict:
    from service.guardrails import InputGuardrail

    guardrail = InputGuardrail()
    user_message = latest_user_message(state)
    result = guardrail.check(user_message)

    if not result.allowed:
        logger.warning("Input guardrail blocked: %s", result.reason)
        return {"guardrail_blocked": True, "guardrail_reason": result.reason}

    return {"guardrail_blocked": False}


def load_memory_node(state: dict, memory_service=None) -> dict:
    from service.observability import MetricsCollector
    collector = MetricsCollector()
    collector.set_metadata("session_id", state.get("session_id"))
    collector.set_metadata("user_id", state.get("user_id"))

    user_id = state.get("user_id")
    if user_id is None or memory_service is None:
        return {"loaded_user_memories": [], "metrics": collector.to_log_dict()}

    with collector.timer("load_memory"):
        memories = memory_service.list_memories(user_id)

    return {"loaded_user_memories": memories, "metrics": collector.to_log_dict()}


def memory_writer_node(state: dict, memory_service=None) -> dict:
    user_id = state.get("user_id")
    if user_id is None or memory_service is None:
        return {"saved_memories": []}

    candidates = list(state.get("memory_candidates") or [])

    if not candidates:
        candidates = _extract_memory_candidates(state)

    saved = []
    for candidate in candidates:
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


def _extract_memory_candidates(state: dict) -> list[dict]:
    conversation = _format_conversation_for_memory(state.get("messages", []))
    if not conversation.strip():
        return []

    try:
        from service.agent_runtime.prompts import PromptRegistry
        from tools.llm_tool import call_llm

        memory_prompt = PromptRegistry().load("agent.memory_writer")
        raw = call_llm(query=conversation, system_instruction=memory_prompt)
        parsed = json.loads(_clean_json(raw))
        return parsed.get("memories", [])
    except Exception:
        logger.warning("Memory extraction via LLM failed, skipping", exc_info=True)
        return []


def _format_conversation_for_memory(messages: list) -> str:
    parts = []
    for msg in messages[-6:]:
        role = "用户" if isinstance(msg, HumanMessage) else "助手"
        parts.append(f"{role}: {msg.content}")
    return "\n".join(parts)


def plan_node(state: dict, planner: LangGraphAgentPlanner) -> dict:
    user_message = latest_user_message(state)
    plan = planner.plan(
        user_message,
        {
            "session_id": state.get("session_id"),
            "user_id": state.get("user_id"),
            "loaded_user_memories": state.get("loaded_user_memories", []),
            "recent_action_ids": state.get("recent_action_ids", []),
            "iteration_count": state.get("iteration_count", 0),
            "recent_evidence": state.get("recent_evidence", []),
            "tool_results": state.get("tool_results", []),
        },
    )
    return {"current_plan": plan}


def route_after_plan(state: dict) -> str:
    plan = state.get("current_plan")
    if plan is None:
        logger.debug("Agent route: no plan → respond")
        return "respond"

    has_evidence = bool(state.get("recent_evidence"))
    completed_tools = {r.get("type", "") for r in state.get("tool_results", [])}

    remaining_calls = [c for c in plan.tool_calls if c.tool_name not in completed_tools]

    if has_evidence and plan.intent in {"recommendation", "knowledge"} and not any(
        c.tool_name in ACTION_TOOL_NAMES for c in remaining_calls
    ):
        logger.debug("Agent route: evidence already present, intent=%s → respond", plan.intent)
        return "respond"

    if plan.intent == "undo_action":
        logger.debug("Agent route: undo_action → undo")
        return "undo"

    next_call = remaining_calls[0] if remaining_calls else None

    if plan.requires_rag and not has_evidence:
        logger.debug("Agent route: intent=%s requires_rag=%s → rag", plan.intent, plan.requires_rag)
        return "rag"

    if next_call is None:
        return "respond"

    if next_call.tool_name in RAG_TOOL_NAMES:
        return "rag"
    if next_call.tool_name in ACTION_TOOL_NAMES:
        logger.debug("Agent route: action tool → action")
        return "action"
    logger.debug("Agent route: intent=%s → respond", plan.intent)
    return "respond"


def evaluate_node(state: dict) -> dict:
    iteration = state.get("iteration_count", 0) + 1
    max_iter = state.get("max_iterations", 5)
    logger.debug("Agent evaluate: iteration=%d/%d", iteration, max_iter)

    if iteration >= max_iter:
        logger.debug("Agent evaluate: max iterations reached → respond")
        return {"iteration_count": iteration, "_next": "respond"}

    plan = state.get("current_plan")
    if plan is None:
        return {"iteration_count": iteration, "_next": "respond"}

    completed_tools = {r.get("type", "") for r in state.get("tool_results", [])}
    pending_calls = [
        call for call in plan.tool_calls
        if call.tool_name not in completed_tools
    ]

    has_pending_action = any(call.tool_name in ACTION_TOOL_NAMES for call in pending_calls)
    has_pending_rag = any(call.tool_name in RAG_TOOL_NAMES for call in pending_calls)

    if has_pending_rag:
        logger.debug("Agent evaluate: pending RAG calls → plan (re-route to rag)")
        return {"iteration_count": iteration, "_next": "plan"}

    if has_pending_action:
        logger.debug("Agent evaluate: pending action calls → plan (re-route to action)")
        return {"iteration_count": iteration, "_next": "plan"}

    has_evidence = bool(state.get("recent_evidence"))
    has_tool_results = bool(state.get("tool_results"))

    if has_evidence or has_tool_results:
        logger.debug("Agent evaluate: all steps done → respond")
        return {"iteration_count": iteration, "_next": "respond"}

    logger.debug("Agent evaluate: no results yet → plan")
    return {"iteration_count": iteration, "_next": "plan"}


def route_after_evaluate(state: dict) -> str:
    return state.get("_next", "respond")


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

        if call.tool_name == "add_to_cart":
            from service.tools.cart_tool import add_to_cart_tool

            dish_id = call.arguments.get("dish_id")
            quantity = call.arguments.get("quantity", 1)
            if dish_id is None:
                return {
                    "success": False,
                    "message": "缺少 dish_id 参数",
                    "undo_available": False,
                }
            add_result = add_to_cart_tool(
                user_id=user_id, dish_id=int(dish_id), quantity=int(quantity), session=self.session,
            )
            journal = ActionJournalService(self.session).record_completed_action(
                session_id=session_id,
                user_id=user_id,
                action_type="add_to_cart",
                undo_policy="remove_item",
                before_snapshot={},
                after_snapshot={"dish_id": dish_id, "quantity": quantity},
                undo_tool="remove_from_cart",
                natural_summary=f"已将菜品加入购物车",
            )
            action_id = self._record_value(journal, "action_id")
            return {
                "success": True,
                "action_id": action_id,
                "message": f"已将菜品加入购物车",
                "undo_available": True,
                "data": add_result,
            }

        if call.tool_name == "remove_from_cart":
            from service.cart_service import CartService

            dish_id = call.arguments.get("dish_id")
            if dish_id is None:
                return {"success": False, "message": "缺少 dish_id 参数", "undo_available": False}
            cart_service = CartService(self.session)
            cart_service.remove_item(user_id, int(dish_id))
            return {
                "success": True,
                "action_id": None,
                "message": "已从购物车移除",
                "undo_available": False,
            }

        if call.tool_name == "save_address":
            from service.tools.address_tool import commit_address_action_tool

            address_data = call.arguments
            result = commit_address_action_tool(user_id=user_id, address=address_data, session=self.session)
            journal = ActionJournalService(self.session).record_completed_action(
                session_id=session_id,
                user_id=user_id,
                action_type="save_address",
                undo_policy="none",
                before_snapshot={},
                after_snapshot=address_data,
                undo_tool="",
                natural_summary="已保存配送地址",
            )
            action_id = self._record_value(journal, "action_id")
            return {
                "success": True,
                "action_id": action_id,
                "message": "已保存配送地址",
                "undo_available": False,
                "data": result,
            }

        if call.tool_name == "upsert_preference":
            from service.tools.preference_tool import upsert_preference_tool

            memory_type = call.arguments.get("memory_type", "food_preference")
            content = call.arguments.get("content", "")
            result = upsert_preference_tool(
                user_id=user_id, memory_type=memory_type, content=content, session=self.session,
            )
            journal = ActionJournalService(self.session).record_completed_action(
                session_id=session_id,
                user_id=user_id,
                action_type="upsert_preference",
                undo_policy=result.get("undo_policy", "none"),
                before_snapshot=result.get("before_snapshot", {}),
                after_snapshot=result.get("after_snapshot", {}),
                undo_tool=result.get("undo_tool", ""),
                natural_summary="已更新用户偏好",
            )
            action_id = self._record_value(journal, "action_id")
            return {
                "success": True,
                "action_id": action_id,
                "message": "已更新用户偏好",
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


def respond_node(state: dict, use_llm: bool = True) -> dict:
    # Handle guardrail-blocked requests
    if state.get("guardrail_blocked"):
        message = "抱歉，您的请求无法处理。请尝试换一种方式提问。"
        payload = {
            "session_id": state.get("session_id"),
            "message": message,
            "response_type": "guardrail_blocked",
            "needs_clarification": False,
            "clarification_question": None,
            "extracted_constraints": None,
            "recommendations": [],
            "comparisons": [],
            "citations": [],
            "suggested_actions": [],
            "pending_action": None,
            "executed_actions": [],
            "undo_available": False,
        }
        return {
            "messages": state.get("messages", []) + [AIMessage(content=message)],
            "response_payload": payload,
        }

    plan = state.get("current_plan")
    evidence = state.get("recent_evidence", [])
    response_type = _external_response_type(plan, state)
    user_message = latest_user_message(state)

    recommendations, citations = _build_structured_data(evidence)
    tool_results = state.get("tool_results", [])

    if evidence and use_llm:
        message = _generate_llm_response(user_message, response_type, evidence)
    elif evidence:
        message = _template_recommendation(recommendations)
    elif tool_results:
        message = tool_results[0].get("message", "操作已完成")
    elif response_type == "greeting":
        message = "你好！我是你的智能点餐助手，可以帮你推荐菜品、查找商家信息、管理购物车。"
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

    from service.observability import MetricsCollector
    collector = MetricsCollector()
    collector.set_metadata("response_type", response_type)
    collector.set_metadata("evidence_count", len(evidence))
    collector.set_metadata("tool_results_count", len(tool_results))
    collector.emit("agent_respond")

    return {
        "messages": state.get("messages", []) + [AIMessage(content=message)],
        "response_payload": payload,
    }


def _build_structured_data(evidence: list[dict]) -> tuple[list[dict], list[dict]]:
    recommendations = []
    citations = []
    for item in evidence:
        facts = item.get("facts", {})
        if item.get("source_type") == "dish":
            recommendations.append({
                "source_type": "dish",
                "merchant_id": item.get("merchant_id"),
                "merchant_name": facts.get("merchant_name", ""),
                "dish_id": facts.get("dish_id"),
                "dish_name": facts.get("dish_name"),
                "price": facts.get("price"),
                "reason": "、".join(item.get("why_matched", [])),
            })
        elif item.get("source_type") == "merchant":
            merchant_id = item.get("merchant_id") or facts.get("merchant_id") or facts.get("id") or 0
            merchant_name = facts.get("merchant_name") or facts.get("name") or item.get("title") or ""
            recommendations.append({
                "source_type": "merchant",
                "merchant_id": merchant_id,
                "merchant_name": merchant_name,
                "dish_id": None,
                "dish_name": None,
                "price": None,
                "reason": "、".join(item.get("why_matched", [])),
            })
        citations.append({
            "source_type": item.get("source_type"),
            "source_id": item.get("source_id"),
            "title": item.get("title"),
            "snippet": item.get("citation", ""),
        })
    return recommendations, citations


def _generate_llm_response(user_message: str, response_type: str, evidence: list[dict]) -> str:
    try:
        from service.agent_runtime.prompts import PromptRegistry
        from tools.llm_tool import call_llm

        evidence_text = _format_evidence_for_llm(evidence)
        system_prompt = PromptRegistry().load("agent.answer_grounded")
        prompt = f"用户消息：{user_message}\n意图：{response_type}\n\n检索到的证据：\n{evidence_text}\n\n请基于证据生成自然回复。"
        return call_llm(query=prompt, system_instruction=system_prompt)
    except Exception:
        logger.warning("LLM response generation failed, falling back to template", exc_info=True)
        recommendations, _ = _build_structured_data(evidence)
        return _template_recommendation(recommendations)


def _format_evidence_for_llm(evidence: list[dict]) -> str:
    lines = []
    for i, item in enumerate(evidence, 1):
        facts = item.get("facts", {})
        if item.get("source_type") == "dish":
            lines.append(
                f"{i}. 菜品：{facts.get('dish_name', '')}（{facts.get('merchant_name', '')}）"
                f" - 价格：{facts.get('price', '')}元"
                f" - 特色：{facts.get('flavor_profile', '')}"
                f" - 匹配原因：{'、'.join(item.get('why_matched', []))}"
            )
        else:
            parts = [f"{i}. 商家：{facts.get('merchant_name', facts.get('name', ''))}"]
            if facts.get('phone'):
                parts.append(f"电话：{facts['phone']}")
            if facts.get('detailed_address'):
                parts.append(f"地址：{facts['detailed_address']}")
            elif facts.get('address'):
                parts.append(f"地址：{facts['address']}")
            if facts.get('business_hours'):
                parts.append(f"营业时间：{facts['business_hours']}")
            parts.append(f"简介：{item.get('citation', '')}")
            lines.append(" - ".join(parts))
    return "\n".join(lines)


def _template_recommendation(recommendations: list[dict]) -> str:
    lines = ["结合商家数据，为你找到以下推荐："]
    for index, item in enumerate(recommendations, start=1):
        if item.get("source_type") == "merchant":
            lines.append(f"{index}. {item['merchant_name']}")
        else:
            lines.append(f"{index}. {item['dish_name']}（{item['merchant_name']}）- {item.get('reason', '')}")
    return "\n".join(lines)


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


def _clean_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text
