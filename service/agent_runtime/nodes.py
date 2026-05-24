import json
import logging

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from service.agent_runtime.planner import ACTION_TOOL_NAMES, RAG_TOOL_NAMES, LangGraphAgentPlanner
from service.agent_runtime.runtime import get_runtime
from service.rag.retriever import AdvancedRagRetriever

logger = logging.getLogger(__name__)


def latest_user_message(state: dict) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


_input_guardrail = None


def _get_input_guardrail():
    global _input_guardrail
    if _input_guardrail is None:
        from service.config import get_config
        from service.guardrails import InputGuardrail
        cfg = get_config().guardrails
        _input_guardrail = InputGuardrail(
            max_length=cfg.max_input_length,
            enable_topic_check=cfg.enable_topic_guardrail,
        )
    return _input_guardrail


def _reset_input_guardrail():
    global _input_guardrail
    _input_guardrail = None


def input_guardrail_node(state: dict) -> dict:
    from service.config import get_config

    # 如果 guardrail 关闭了，就直接放行，避免不必要的计算
    if not get_config().guardrails.enable_input_guardrail:
        return {"guardrail_blocked": False}

    guardrail = _get_input_guardrail()
    user_message = latest_user_message(state)
    result = guardrail.check(user_message)

    if not result.allowed:
        logger.warning("Input guardrail blocked: category=%s reason=%s", result.category, result.reason)
        return {
            "guardrail_blocked": True,
            "guardrail_reason": result.reason,
            "guardrail_category": result.category,
        }

    return {"guardrail_blocked": False}


def load_memory_node(state: dict, config: RunnableConfig | None = None) -> dict:
    from service.observability import MetricsCollector

    runtime = get_runtime(config)
    memory_service = runtime.memory_service if runtime else None

    collector = MetricsCollector()
    collector.set_metadata("session_id", state.get("session_id"))
    collector.set_metadata("user_id", state.get("user_id"))

    # Reset per-turn transient state so previous turns don't bleed through
    turn_reset = {
        "tool_results": [],
        "recent_evidence": [],
        "iteration_count": 0,
        "current_plan": None,
    }

    user_id = state.get("user_id")
    if user_id is None or memory_service is None:
        return {**turn_reset, "loaded_user_memories": [], "metrics": collector.to_log_dict()}

    with collector.timer("load_memory"):
        memories = memory_service.list_memories(user_id)

    return {**turn_reset, "loaded_user_memories": memories, "metrics": collector.to_log_dict()}


def memory_writer_node(state: dict, config: RunnableConfig | None = None) -> dict:
    runtime = get_runtime(config)
    memory_service = runtime.memory_service if runtime else None

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


def _format_recent_turns(messages: list, max_turns: int = 3) -> str:
    """Format the last *max_turns* complete turns (human+ai pairs) excluding
    the current (last) human message.

    Returns an empty string when there are no previous turns, so callers can
    cheaply skip injection when the conversation just started.
    """
    # Drop the trailing human message (current turn)
    history = list(messages)
    if history and isinstance(history[-1], HumanMessage):
        history = history[:-1]

    # Walk backwards to collect at most max_turns pairs
    pairs: list[tuple[str, str]] = []
    i = len(history) - 1
    while i >= 1 and len(pairs) < max_turns:
        ai_msg = history[i]
        human_msg = history[i - 1]
        if isinstance(ai_msg, AIMessage) and isinstance(human_msg, HumanMessage):
            pairs.append((str(human_msg.content), str(ai_msg.content)))
            i -= 2
        else:
            i -= 1

    if not pairs:
        return ""

    pairs.reverse()
    lines = []
    for human, ai in pairs:
        lines.append(f"用户: {human}")
        lines.append(f"助手: {ai}")
    return "\n".join(lines)


def plan_node(state: dict, config: RunnableConfig | None = None) -> dict:
    # Reuse current plan if it still has pending (uncompleted) calls.
    # This prevents step_id collision from counter-reset on re-planning.
    current_plan = state.get("current_plan")
    if current_plan and current_plan.tool_calls:
        completed_step_ids = {
            r.get("step_id") or r.get("type", "")
            for r in state.get("tool_results", [])
        }
        pending = [c for c in current_plan.tool_calls if c.step_id not in completed_step_ids]
        if pending:
            return {"current_plan": current_plan}

    # All calls completed (or no plan) — call LLM for (re-)planning
    runtime = get_runtime(config)
    planner = (runtime.planner if runtime else None) or _get_default_planner()

    user_message = latest_user_message(state)
    conversation_history = _format_recent_turns(state.get("messages", []), max_turns=3)
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
            "conversation_history": conversation_history,
            "last_recommendations": state.get("last_recommendations", []),
        },
    )

    # De-conflict step_ids: re-plan generates step_ids from counter=0,
    # which may collide with already-completed step_ids in tool_results.
    used_step_ids = {
        r.get("step_id") or r.get("type", "")
        for r in state.get("tool_results", [])
    }
    _deconflict_step_ids(plan, used_step_ids)

    return {"current_plan": plan}


def _deconflict_step_ids(plan, used_step_ids: set[str]) -> None:
    """Reassign any step_id in plan.tool_calls that collides with used_step_ids,
    or is empty (e.g. from _rule_plan which doesn't set step_id)."""
    for call in plan.tool_calls:
        if not call.step_id or call.step_id in used_step_ids:
            suffix = 0
            while f"{call.tool_name}_{suffix}" in used_step_ids:
                suffix += 1
            call.step_id = f"{call.tool_name}_{suffix}"
        used_step_ids.add(call.step_id)


# ── Cached default planner (module-level singleton) ─────────────────
_default_planner: LangGraphAgentPlanner | None = None


def _get_default_planner() -> LangGraphAgentPlanner:
    global _default_planner
    if _default_planner is None:
        _default_planner = LangGraphAgentPlanner()
    return _default_planner


def route_after_plan(state: dict) -> str:
    plan = state.get("current_plan")
    if plan is None:
        logger.debug("Agent route: no plan → respond")
        return "respond"

    has_evidence = bool(state.get("recent_evidence"))
    completed_step_ids = {r.get("step_id") or r.get("type", "") for r in state.get("tool_results", [])}
    remaining_calls = [c for c in plan.tool_calls if c.step_id not in completed_step_ids]

    if has_evidence and plan.intent in {"recommendation", "knowledge"} and not any(
        c.tool_name in ACTION_TOOL_NAMES | RAG_TOOL_NAMES for c in remaining_calls
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


# ── Unfulfilled intent detection ─────────────────────────────────────

_ACTION_INTENT_MAPPING = {
    "add_to_cart": ["加入购物车", "加购物车", "加到购物车", "都加入", "加购", "买"],
    "remove_from_cart": ["移除", "从购物车删", "去掉"],
    "cart_clear": ["清空购物车", "全部删除"],
    "upsert_preference": ["记住", "偏好", "不吃", "过敏"],
    "save_address": ["保存地址", "加入地址"],
}

_COMPOUND_QUERY_MARKERS = ["再推荐", "再来", "还要", "另外推荐", "还推荐", "同时推荐"]

_CUISINE_KEYWORDS = {
    "川菜": "川菜", "湘菜": "湘菜", "粤菜": "粤菜", "日料": "日韩料理",
    "韩餐": "日韩料理", "西餐": "西餐", "火锅": "火锅", "烧烤": "烧烤",
    "咖啡": "咖啡甜品", "甜品": "咖啡甜品", "轻食": "轻食",
}


def _has_unfulfilled_intent(state: dict) -> bool:
    return _has_unfulfilled_action_intent(state) or _has_unfulfilled_retrieval_intent(state)


def _has_unfulfilled_action_intent(state: dict) -> bool:
    user_message = latest_user_message(state)
    completed_action_tools = {
        r.get("type", "")
        for r in state.get("tool_results", [])
        if r.get("success", False) and r.get("type", "") in ACTION_TOOL_NAMES
    }
    for tool_name, keywords in _ACTION_INTENT_MAPPING.items():
        if any(kw in user_message for kw in keywords):
            if tool_name not in completed_action_tools:
                return True
    return False


def _has_unfulfilled_retrieval_intent(state: dict) -> bool:
    user_message = latest_user_message(state)

    if not any(marker in user_message for marker in _COMPOUND_QUERY_MARKERS):
        return False

    mentioned = set()
    for keyword, cuisine in _CUISINE_KEYWORDS.items():
        if keyword in user_message:
            mentioned.add(cuisine)

    if len(mentioned) < 2:
        return False

    evidence = state.get("recent_evidence", [])
    covered = {
        e.get("facts", {}).get("cuisine_type", "")
        for e in evidence
        if e.get("source_type") == "dish"
    }
    return not mentioned.issubset(covered)


def evaluate_node(state: dict) -> dict:
    iteration = state.get("iteration_count", 0) + 1
    max_iter = state.get("max_iterations", 5)
    logger.debug("Agent evaluate: iteration=%d/%d", iteration, max_iter)

    # Merge iteration_count into cumulative metrics
    existing_metrics = dict(state.get("metrics") or {})
    existing_metrics["iteration_count"] = iteration

    if iteration >= max_iter:
        logger.debug("Agent evaluate: max iterations reached → respond")
        return {"iteration_count": iteration, "_next": "respond", "metrics": existing_metrics}

    plan = state.get("current_plan")
    if plan is None:
        return {"iteration_count": iteration, "_next": "respond", "metrics": existing_metrics}

    completed_step_ids = {r.get("step_id") or r.get("type", "") for r in state.get("tool_results", [])}
    pending_calls = [
        call for call in plan.tool_calls
        if call.step_id not in completed_step_ids
    ]

    has_pending_action = any(call.tool_name in ACTION_TOOL_NAMES for call in pending_calls)
    has_pending_rag = any(call.tool_name in RAG_TOOL_NAMES for call in pending_calls)

    if has_pending_rag:
        logger.debug("Agent evaluate: pending RAG calls → plan (re-route to rag)")
        return {"iteration_count": iteration, "_next": "plan", "metrics": existing_metrics}

    if has_pending_action:
        logger.debug("Agent evaluate: pending action calls → plan (re-route to action)")
        return {"iteration_count": iteration, "_next": "plan", "metrics": existing_metrics}

    has_evidence = bool(state.get("recent_evidence"))
    has_tool_results = bool(state.get("tool_results"))

    if has_evidence or has_tool_results:
        # Check for unfulfilled follow-up intent before going to respond
        if _has_unfulfilled_intent(state):
            logger.debug("Agent evaluate: unfulfilled intent detected → plan (continuation)")
            return {"iteration_count": iteration, "_next": "plan", "metrics": existing_metrics}
        logger.debug("Agent evaluate: all steps done → respond")
        return {"iteration_count": iteration, "_next": "respond", "metrics": existing_metrics}

    logger.debug("Agent evaluate: no results yet → plan")
    return {"iteration_count": iteration, "_next": "plan", "metrics": existing_metrics}


def route_after_evaluate(state: dict) -> str:
    return state.get("_next", "respond")


def _build_call_scoped_plan(plan, call_args):
    """Create a shallow copy of plan with filters scoped to a specific tool_call.

    IMPORTANT: When multiple RAG calls exist, plan-level filters are the UNION of
    all calls' arguments (merged by _merge_read_tool_arguments). We must NOT inherit
    plan-level list filters that don't belong to THIS call. For list-type filter keys,
    we use ONLY what call_args provides (defaulting to empty). For scalar keys, we
    fall back to the plan-level value since scalars don't suffer from cross-call leakage.
    """
    import copy
    scoped = copy.copy(plan)
    plan_filters = dict(plan.filters or {})

    # List-type keys: use ONLY call_args value, default to empty list.
    # This prevents cross-call leakage (e.g. required_keywords:["咖啡"] leaking into a 川菜 query).
    _LIST_FILTER_KEYS = (
        "cuisine_types", "flavor_preferences", "required_keywords",
        "forbidden_keywords", "exclude_allergens", "source_types",
    )
    # Scalar keys: fall back to plan-level if call_args doesn't specify.
    _SCALAR_FILTER_KEYS = ("limit", "sort_by", "price_preference", "budget_max")

    filters = {}
    for key in _LIST_FILTER_KEYS:
        if key in call_args and call_args[key] is not None:
            filters[key] = call_args[key]
        else:
            filters[key] = []

    for key in _SCALAR_FILTER_KEYS:
        if key in call_args and call_args[key] is not None:
            filters[key] = call_args[key]
        else:
            filters[key] = plan_filters.get(key)

    if call_args.get("query"):
        scoped.normalized_query = call_args["query"]

    scoped.filters = filters
    return scoped


def rag_node(state: dict, config: RunnableConfig | None = None) -> dict:
    from service.config import get_config

    runtime = get_runtime(config)
    retriever = (runtime.retriever if runtime else None) or AdvancedRagRetriever()

    rag_cfg = get_config().rag
    plan = state["current_plan"]

    # Find the NEXT pending RAG call (single-step execution)
    completed_step_ids = {
        r.get("step_id") or r.get("type", "")
        for r in state.get("tool_results", [])
    }
    next_rag_call = next(
        (c for c in plan.tool_calls
         if c.tool_name in RAG_TOOL_NAMES and c.step_id not in completed_step_ids),
        None,
    )

    if next_rag_call is None:
        # Fallback: plan has requires_rag but no explicit RAG tool_calls.
        # Use plan's normalized_query directly (backward compatible).
        if plan.requires_rag and not any(r.get("type", "") in RAG_TOOL_NAMES for r in state.get("tool_results", [])):
            effective_query = plan.normalized_query or latest_user_message(state)
            call_plan = plan
            synthetic_step_id = "recommend_dishes_0"
        else:
            return {}  # No pending RAG call
    else:
        # Use this call's arguments to determine retrieval parameters
        call_args = next_rag_call.arguments or {}
        effective_query = (
            call_args.get("query")
            or plan.normalized_query
            or latest_user_message(state)
        )
        # Build a scoped plan with this call's filters
        call_plan = _build_call_scoped_plan(plan, call_args)
        synthetic_step_id = next_rag_call.step_id

    evidence = retriever.retrieve(
        effective_query,
        agent_plan=call_plan,
        memories=state.get("loaded_user_memories", []),
        limit=rag_cfg.output_limit_default,
        max_limit=rag_cfg.output_limit_max,
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

    # Evidence accumulation — append, don't replace
    existing_evidence = list(state.get("recent_evidence", []))
    seen_keys = {(e.get("source_type"), e.get("source_id")) for e in existing_evidence}
    for item in serialized:
        key = (item["source_type"], item["source_id"])
        if key not in seen_keys:
            existing_evidence.append(item)
            seen_keys.add(key)

    # Mark only THIS step complete
    existing_results = list(state.get("tool_results", []))
    existing_results.append({
        "type": next_rag_call.tool_name if next_rag_call else "recommend_dishes",
        "step_id": synthetic_step_id,
        "success": True,
        "message": f"检索到 {len(serialized)} 条结果",
        "data": {},
    })

    return {"recent_evidence": existing_evidence, "tool_results": existing_results}


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
        completed_step_ids = {r.get("step_id") or r.get("type", "") for r in state.get("tool_results", [])}
        call = next(
            (item for item in plan.tool_calls
             if item.tool_name in ACTION_TOOL_NAMES and item.step_id not in completed_step_ids),
            None,
        )
        if call is None:
            return {
                "success": False,
                "message": "没有待执行的操作",
                "undo_available": False,
            }
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

            # Evidence bridging fallback: if LLM omitted dish_id, pick from evidence.
            # Use index-based mapping: the Nth pending add_to_cart maps to the Nth dish evidence.
            if dish_id is None:
                dish_evidence = [
                    e for e in state.get("recent_evidence", [])
                    if e.get("source_type") == "dish"
                ]
                if dish_evidence:
                    # Count how many add_to_cart calls already completed
                    completed_cart_count = sum(
                        1 for r in state.get("tool_results", [])
                        if r.get("type") == "add_to_cart" and r.get("success")
                    )
                    ev_index = min(completed_cart_count, len(dish_evidence) - 1)
                    dish_id = dish_evidence[ev_index].get("facts", {}).get("dish_id")

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


def action_node(state: dict, config: RunnableConfig | None = None) -> dict:
    runtime = get_runtime(config)
    executor = (runtime.action_executor if runtime else None) or LocalActionExecutor()
    plan = state["current_plan"]

    # Determine which action tool will be executed next
    completed_step_ids = {r.get("step_id") or r.get("type", "") for r in state.get("tool_results", [])}
    next_action_call = next(
        (c for c in plan.tool_calls
         if c.tool_name in ACTION_TOOL_NAMES and c.step_id not in completed_step_ids),
        None,
    )
    executed_tool_name = next_action_call.tool_name if next_action_call else ""
    executed_step_id = next_action_call.step_id if next_action_call else ""

    result = executor.execute_action(plan, state)

    # Accumulate tool_results instead of replacing
    existing_results = list(state.get("tool_results", []))
    existing_results.append(_normalize_tool_result(result, state, executed_tool_name, step_id=executed_step_id))

    recent_ids = list(state.get("recent_action_ids", []))
    if result.get("action_id"):
        recent_ids.append(result["action_id"])
    return {
        "tool_results": existing_results,
        "recent_action_ids": recent_ids,
    }


def undo_node(state: dict, config: RunnableConfig | None = None) -> dict:
    runtime = get_runtime(config)
    executor = (runtime.action_executor if runtime else None) or LocalActionExecutor()
    result = executor.undo_last(state)
    existing_results = list(state.get("tool_results", []))
    existing_results.append(_normalize_tool_result(result, state, "undo_last_action", step_id="undo_last_action_0"))
    return {"tool_results": existing_results}


def _normalize_tool_result(result: dict, state: dict, executed_tool_name: str = "", step_id: str = "") -> dict:
    tool_name = executed_tool_name
    if not tool_name:
        plan = state.get("current_plan")
        if plan and plan.tool_calls:
            tool_name = plan.tool_calls[0].tool_name
    data = dict(result.get("data") or {})
    for key in ("action_id", "undo_available"):
        if key in result:
            data[key] = result[key]
    return {
        "type": result.get("type") or tool_name or "unknown",
        "step_id": step_id,
        "success": bool(result.get("success", False)),
        "message": result.get("message", ""),
        "data": data,
    }


def _append_action_confirmations(message: str, tool_results: list[dict]) -> str:
    """Append action confirmation lines to a message. Used by both template
    and LLM-fallback paths to ensure action results are never silently dropped."""
    if not tool_results:
        return message
    action_msgs = [
        r.get("message", "")
        for r in tool_results
        if r.get("success") and r.get("type", "") in ACTION_TOOL_NAMES
    ]
    if action_msgs:
        message += "\n\n" + "\n".join(f"- {m}" for m in action_msgs)
    return message


def respond_node(state: dict, config: RunnableConfig | None = None) -> dict:
    runtime = get_runtime(config)
    use_llm = runtime.use_llm_response if runtime else True
    # Handle guardrail-blocked requests
    if state.get("guardrail_blocked"):
        category = state.get("guardrail_category", "safety")
        if category == "off_topic":
            message = (
                "我是你的智能点餐助手，可以帮你推荐菜品、查找商家信息、"
                "管理购物车和配送地址。请问有什么点餐相关的需求吗？"
            )
            response_type = "off_topic"
        else:
            message = "抱歉，您的请求无法处理。请尝试换一种方式提问。"
            response_type = "guardrail_blocked"
        payload = {
            "session_id": state.get("session_id"),
            "message": message,
            "response_type": response_type,
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
    conversation_history = _format_recent_turns(state.get("messages", []), max_turns=2)

    recommendations, citations = _build_structured_data(evidence)
    tool_results = state.get("tool_results", [])

    if evidence and use_llm:
        message = _generate_llm_response(
            user_message, response_type, evidence, conversation_history,
            tool_results=tool_results,
        )
    elif evidence:
        message = _template_recommendation(recommendations)
        message = _append_action_confirmations(message, tool_results)
    elif tool_results:
        message = tool_results[0].get("message", "操作已完成")
    elif response_type == "greeting":
        message = "你好！我是你的智能点餐助手，可以帮你推荐菜品、查找商家信息、管理购物车。"
    elif response_type == "unsupported":
        message = (
            "这个问题超出了我的能力范围。我是你的智能点餐助手，"
            "可以帮你推荐菜品、查找商家信息、管理购物车和配送地址。"
            "请问有什么点餐相关的需求吗？"
        )
    else:
        message = "我没有找到足够匹配的结果，可以换个说法再试试。"

    if evidence and use_llm:
        from service.config import get_config
        if get_config().guardrails.enable_output_guardrail:
            from service.guardrails import OutputGuardrail
            output_result = OutputGuardrail().check(message, evidence)
            if not output_result.allowed:
                logger.warning("Output guardrail triggered: %s, falling back to template", output_result.reason)
                message = _append_action_confirmations(
                    _template_recommendation(recommendations),
                    tool_results,
                )

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

    # Merge respond-node metrics into cumulative state["metrics"]
    existing_metrics = dict(state.get("metrics") or {})
    existing_metrics["response_type"] = response_type
    existing_metrics["evidence_count"] = len(evidence)
    existing_metrics["tool_results_count"] = len(tool_results)

    result: dict = {
        "messages": state.get("messages", []) + [AIMessage(content=message)],
        "response_payload": payload,
        "metrics": existing_metrics,
    }
    # Carry structured recommendations forward so the next turn can resolve
    # references like "第一个加购物车" to a concrete dish_id.
    if recommendations:
        result["last_recommendations"] = recommendations
    return result


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


def _generate_llm_response(
    user_message: str,
    response_type: str,
    evidence: list[dict],
    conversation_history: str = "",
    tool_results: list[dict] | None = None,
) -> str:
    try:
        from service.agent_runtime.prompts import PromptRegistry
        from tools.llm_tool import call_llm

        evidence_text = _format_evidence_for_llm(evidence)
        system_prompt = PromptRegistry().load("agent.answer_grounded")
        parts = []
        if conversation_history:
            parts.append(f"对话历史：\n{conversation_history}\n")
        parts.append(f"用户最新消息：{user_message}")
        parts.append(f"意图：{response_type}")
        parts.append(f"\n检索到的证据：\n{evidence_text}")

        # Inject completed action results for compound scenarios
        if tool_results:
            action_lines = []
            for r in tool_results:
                if r.get("type", "") in ACTION_TOOL_NAMES:
                    status = "成功" if r.get("success") else "失败"
                    action_lines.append(f"- {r.get('message', '')}（{status}）")
            if action_lines:
                parts.append(f"\n已完成的操作：\n" + "\n".join(action_lines))

        parts.append("\n请基于证据和已完成操作生成自然回复。")
        prompt = "\n".join(parts)
        return call_llm(query=prompt, system_instruction=system_prompt)
    except Exception:
        logger.warning("LLM response generation failed, falling back to template", exc_info=True)
        recommendations, _ = _build_structured_data(evidence)
        fallback = _template_recommendation(recommendations)
        return _append_action_confirmations(fallback, tool_results or [])


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
    # Compound scenario: evidence + successful action → action_completed
    tool_results = state.get("tool_results", [])
    has_successful_action = any(
        r.get("success") and r.get("type", "") in ACTION_TOOL_NAMES
        for r in tool_results
    )
    if has_successful_action:
        return "action_completed"
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
