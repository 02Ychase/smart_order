from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from service.agent_runtime.prompts import PromptRegistry
from service.agent_runtime.schemas import AgentPlanSchema, FiltersSchema, GraphToolCallSchema
from service.agent_runtime.state import AgentPlan, GraphToolCall
from tools.llm_tool import call_llm_with_retry

logger = logging.getLogger(__name__)


RAG_TOOL_NAMES = {"recommend_dishes", "search_catalog"}
ACTION_TOOL_NAMES = {"cart_clear", "add_to_cart", "remove_from_cart", "save_address", "upsert_preference"}
UNDO_TOOL_NAMES = {"undo_last_action"}
ALLOWED_TOOL_NAMES = RAG_TOOL_NAMES | ACTION_TOOL_NAMES | UNDO_TOOL_NAMES
SEARCH_TOOL_ALIASES = {
    "search_dishes": "recommend_dishes",
    "search_food": "recommend_dishes",
    "search_menu": "search_catalog",
    "search_catalog": "search_catalog",
    "search_cafes": "search_catalog",
    "search_coffee": "search_catalog",
    "search_merchants": "search_catalog",
    "search_restaurants": "search_catalog",
    "search_stores": "search_catalog",
}
COUNT_PATTERN = re.compile(r"(\d+)\s*(?:个|道|份|款|家)")
COFFEE_TARGETS = {"咖啡", "咖啡甜品"}


class LangGraphAgentPlanner:
    def __init__(self, prompts: PromptRegistry | None = None) -> None:
        self.prompts = prompts or PromptRegistry()
        self._model_name = os.getenv("MODEL_NAME")
        self._structured_llm = None

        if self._model_name:
            try:
                from langchain.chat_models import init_chat_model

                llm = init_chat_model(model=self._model_name, model_provider="openai")
                self._structured_llm = llm.with_structured_output(AgentPlanSchema)
            except Exception:
                logger.warning(
                    "Failed to initialize structured output LLM for model=%s, will fall back",
                    self._model_name,
                    exc_info=True,
                )

    def plan(self, user_message: str, context: dict[str, Any]) -> AgentPlan:
        human_input = self._build_human_input(user_message, context)

        # 1. Structured output path (production, primary)
        if self._structured_llm is not None:
            try:
                schema_result = self._structured_llm.invoke([
                    ("system", self.prompts.load("agent.planner")),
                    ("human", human_input),
                ])
                plan = self._schema_to_plan(schema_result)
                return self._apply_user_message_hints(plan, user_message)
            except Exception:
                logger.warning(
                    "Planner structured LLM call failed, falling back",
                    exc_info=True,
                )

        # 2. Direct call_llm_with_retry path (fallback when _structured_llm init failed but _model_name exists)
        if self._model_name:
            try:
                raw = call_llm_with_retry(
                    query=json.dumps({"message": user_message, "context": context}, ensure_ascii=False),
                    system_instruction=self.prompts.load("agent.planner"),
                )
                return self._apply_user_message_hints(self._parse(raw), user_message)
            except Exception:
                logger.warning("Planner LLM call failed, falling back to rule-based plan", exc_info=True)
                return self._apply_user_message_hints(self._rule_plan(user_message, context), user_message)

        # 3. No LLM configured
        logger.info("No LLM configured, using rule-based planner")
        return self._apply_user_message_hints(self._rule_plan(user_message, context), user_message)

    @staticmethod
    def _build_human_input(user_message: str, context: dict[str, Any]) -> str:
        """Build composite human message that includes conversation history,
        last recommendations, and ReAct observation context so both structured
        and fallback LLM paths receive the same multi-turn context."""
        parts: list[str] = []

        conversation_history = context.get("conversation_history", "")
        if conversation_history:
            parts.append(f"## 对话历史\n{conversation_history}")

        last_recs = context.get("last_recommendations", [])
        if last_recs:
            rec_lines = []
            for idx, rec in enumerate(last_recs, 1):
                name = rec.get("dish_name") or rec.get("merchant_name") or ""
                dish_id = rec.get("dish_id", "")
                price = rec.get("price", "")
                line = f"{idx}. {name}"
                if dish_id:
                    line += f" (dish_id={dish_id})"
                if price:
                    line += f" {price}元"
                rec_lines.append(line)
            parts.append("## 上一轮推荐结果\n" + "\n".join(rec_lines))

        # ReAct observation: evidence from completed RAG calls
        recent_evidence = context.get("recent_evidence", [])
        if recent_evidence:
            evidence_lines = []
            for idx, item in enumerate(recent_evidence, 1):
                facts = item.get("facts", {})
                source_type = item.get("source_type", "")
                if source_type == "dish":
                    line = (
                        f"{idx}. {facts.get('dish_name', '')} "
                        f"(dish_id={facts.get('dish_id', '')}, "
                        f"商家={facts.get('merchant_name', '')}, "
                        f"{facts.get('price', '')}元, "
                        f"{facts.get('cuisine_type', '')}/{facts.get('flavor_profile', '')})"
                    )
                else:
                    line = (
                        f"{idx}. {facts.get('merchant_name', facts.get('name', ''))} "
                        f"(merchant_id={facts.get('merchant_id', facts.get('id', ''))})"
                    )
                evidence_lines.append(line)
            parts.append("## 本轮已检索到的结果\n" + "\n".join(evidence_lines))

        # ReAct observation: completed tool actions
        tool_results = context.get("tool_results", [])
        if tool_results:
            result_lines = []
            for r in tool_results:
                status = "成功" if r.get("success") else "失败"
                result_lines.append(
                    f"- {r.get('step_id', r.get('type', ''))}: {status} - {r.get('message', '')}"
                )
            parts.append("## 本轮已完成的操作\n" + "\n".join(result_lines))

        parts.append(f"## 用户最新消息\n{user_message}")
        return "\n\n".join(parts)

    # 把 LLM 结构化输出的 AgentPlanSchema，转换成系统内部真正执行用的 
    # AgentPlan，并在转换过程中做校正、规范化和兜底。
    def _schema_to_plan(self, schema: AgentPlanSchema) -> AgentPlan:
        """Convert a Pydantic AgentPlanSchema to the AgentPlan dataclass.

        Applies the same post-processing as _parse(): normalizes tool names,
        merges read tool arguments, enforces requires_rag for certain intents,
        and validates writes_database.
        """
        intent = schema.intent or "unsupported"
        filters = self._default_filters()
        schema_filters = schema.filters
        if schema_filters:
            for key in self._default_filters():
                value = getattr(schema_filters, key, None)
                if value is not None:
                    filters[key] = value

        raw_calls = [item.model_dump() for item in (schema.tool_calls or [])]
        tool_calls = self._parse_tool_calls(raw_calls, intent)
        normalized_query = str(schema.normalized_query or "")
        normalized_query = self._merge_read_tool_arguments(
            filters=filters,
            tool_calls=tool_calls,
            normalized_query=normalized_query,
        )
        requires_rag = self._parse_bool(schema.requires_rag)
        if intent in {"recommendation", "knowledge"} or any(call.tool_name in RAG_TOOL_NAMES for call in tool_calls):
            requires_rag = True

        return AgentPlan(
            intent=intent,
            normalized_query=normalized_query,
            requires_rag=requires_rag,
            filters=filters,
            tool_calls=tool_calls,
            should_answer_directly=self._parse_bool(schema.should_answer_directly),
            response_hint=schema.response_hint or "",
        )

    def _parse(self, raw: str | dict[str, Any]) -> AgentPlan:
        parsed = raw if isinstance(raw, dict) else json.loads(self._clean_json(raw))
        intent = parsed.get("intent", "unsupported")
        filters = self._default_filters()
        filters.update(parsed.get("filters") or {})
        tool_calls = self._parse_tool_calls(parsed.get("tool_calls") or [], intent)
        normalized_query = str(parsed.get("normalized_query") or "")
        normalized_query = self._merge_read_tool_arguments(
            filters=filters,
            tool_calls=tool_calls,
            normalized_query=normalized_query,
        )
        requires_rag = self._parse_bool(parsed.get("requires_rag", False))
        if intent in {"recommendation", "knowledge"} or any(call.tool_name in RAG_TOOL_NAMES for call in tool_calls):
            requires_rag = True
        return AgentPlan(
            intent=intent,
            normalized_query=normalized_query,
            requires_rag=requires_rag,
            filters=filters,
            tool_calls=tool_calls,
            should_answer_directly=self._parse_bool(parsed.get("should_answer_directly", True)),
            response_hint=parsed.get("response_hint", ""),
        )

    @staticmethod
    def _default_filters() -> dict[str, Any]:
        return {
            "cuisine_types": [],
            "flavor_preferences": [],
            "budget_max": None,
            "party_size": None,
            "exclude_allergens": [],
            "required_keywords": [],
            "forbidden_keywords": [],
            "source_types": [],
            "limit": None,
            "sort_by": None,
            "price_preference": None,
        }

    def _parse_tool_calls(self, raw_calls: list[dict[str, Any]], intent: str) -> list[GraphToolCall]:
        calls: list[GraphToolCall] = []
        tool_name_counter: dict[str, int] = {}
        seen_step_ids: set[str] = set()
        for item in raw_calls:
            if not isinstance(item, dict):
                continue
            raw_name = str(item.get("tool_name") or item.get("name") or "")
            tool_name = self._normalize_tool_name(raw_name, intent)
            if tool_name is None:
                continue
            arguments = item.get("arguments") or item.get("parameters") or {}
            if not isinstance(arguments, dict):
                arguments = {}
            writes_database = self._parse_bool(item.get("writes_database", False))
            if tool_name in RAG_TOOL_NAMES:
                writes_database = False
            if tool_name in ACTION_TOOL_NAMES | UNDO_TOOL_NAMES:
                writes_database = True
            count = tool_name_counter.get(tool_name, 0)
            step_id = item.get("step_id") or f"{tool_name}_{count}"
            if step_id in seen_step_ids:
                continue
            tool_name_counter[tool_name] = count + 1
            seen_step_ids.add(step_id)
            calls.append(
                GraphToolCall(
                    tool_name=tool_name,
                    arguments=arguments,
                    writes_database=writes_database,
                    step_id=step_id,
                )
            )
        return calls

    @staticmethod
    def _normalize_tool_name(raw_name: str, intent: str) -> str | None:
        tool_name = raw_name.strip()
        if tool_name in ALLOWED_TOOL_NAMES:
            return tool_name
        if tool_name in SEARCH_TOOL_ALIASES:
            return SEARCH_TOOL_ALIASES[tool_name]
        if tool_name.startswith("search_"):
            if any(term in tool_name for term in ("cafe", "coffee", "merchant", "restaurant", "store", "shop")):
                return "search_catalog"
            if intent == "recommendation":
                return "recommend_dishes"
            if intent == "knowledge":
                return "search_catalog"
        return None

    def _merge_read_tool_arguments(
        self,
        *,
        filters: dict[str, Any],
        tool_calls: list[GraphToolCall],
        normalized_query: str,
    ) -> str:
        query = normalized_query
        for call in tool_calls:
            if call.tool_name not in RAG_TOOL_NAMES:
                continue
            arguments = call.arguments
            if not query and arguments.get("query"):
                query = str(arguments["query"])
            self._merge_list_filter(filters, "cuisine_types", arguments.get("cuisine_types") or arguments.get("cuisine_type") or arguments.get("cuisine"))
            self._merge_list_filter(filters, "flavor_preferences", arguments.get("flavor_preferences") or arguments.get("preferences") or arguments.get("flavor"))
            self._merge_list_filter(filters, "exclude_allergens", arguments.get("exclude_allergens"))
            self._merge_list_filter(filters, "required_keywords", arguments.get("required_keywords"))
            self._merge_list_filter(filters, "forbidden_keywords", arguments.get("forbidden_keywords"))
            self._merge_list_filter(filters, "source_types", arguments.get("source_types") or arguments.get("source_type"))
            for key in ("budget_max", "party_size", "merchant_name", "limit", "sort_by", "price_preference"):
                if filters.get(key) in (None, "", []):
                    value = arguments.get(key)
                    if value is None and key == "budget_max":
                        value = arguments.get("budget")
                    if value is not None:
                        filters[key] = value
        return query

    def _apply_user_message_hints(self, plan: AgentPlan, user_message: str) -> AgentPlan:
        if plan.intent not in {"recommendation", "knowledge"}:
            return plan
        filters = dict(plan.filters or {})
        limit = self._extract_requested_limit(user_message)
        if limit is not None:
            filters["limit"] = limit
        if any(term in user_message for term in ("最贵", "价格最高", "最高价")):
            filters["sort_by"] = "price_desc"
            filters["price_preference"] = "most_expensive"
        elif any(term in user_message for term in ("最便宜", "价格最低", "最低价")):
            filters["sort_by"] = "price_asc"
            filters["price_preference"] = "least_expensive"
        plan.filters = filters
        self._split_compound_recommendation_calls(plan, requested_limit=limit)
        self._apply_requested_limit_to_rag_calls(plan, requested_limit=limit)
        return plan

    def _split_compound_recommendation_calls(
        self,
        plan: AgentPlan,
        *,
        requested_limit: int | None = None,
    ) -> None:
        if plan.intent != "recommendation":
            return

        if plan.tool_calls:
            if len(plan.tool_calls) != 1 or plan.tool_calls[0].tool_name != "recommend_dishes":
                return
            base_args = dict(plan.tool_calls[0].arguments or {})
        else:
            if not plan.requires_rag:
                return
            base_args = {"query": plan.normalized_query}

        targets = self._target_list(
            base_args.get("cuisine_types")
            or base_args.get("cuisine_type")
            or base_args.get("cuisine")
            or (plan.filters or {}).get("cuisine_types")
        )
        if len(targets) < 2:
            return

        per_target_limit = self._compound_target_limit(
            requested_limit=requested_limit,
            raw_limit=base_args.get("limit") or (plan.filters or {}).get("limit"),
            target_count=len(targets),
        )

        common_args = dict(base_args)
        for key in ("query", "cuisine_types", "cuisine_type", "cuisine", "limit"):
            common_args.pop(key, None)

        split_calls: list[GraphToolCall] = []
        for idx, target in enumerate(targets):
            arguments = dict(common_args)
            arguments["query"] = f"推荐{target}"
            arguments["cuisine_types"] = [target]
            if per_target_limit is not None:
                arguments["limit"] = per_target_limit
            if target in COFFEE_TARGETS:
                required_keywords = self._target_list(arguments.get("required_keywords"))
                if "咖啡" not in required_keywords:
                    required_keywords.append("咖啡")
                arguments["required_keywords"] = required_keywords

            split_calls.append(
                GraphToolCall(
                    tool_name="recommend_dishes",
                    arguments=arguments,
                    writes_database=False,
                    step_id=f"recommend_dishes_{idx}",
                )
            )

        plan.tool_calls = split_calls

    @staticmethod
    def _apply_requested_limit_to_rag_calls(
        plan: AgentPlan,
        *,
        requested_limit: int | None,
    ) -> None:
        if requested_limit is None:
            return
        rag_calls = [call for call in plan.tool_calls if call.tool_name in RAG_TOOL_NAMES]
        if len(rag_calls) < 2:
            return
        for call in rag_calls:
            call.arguments.setdefault("limit", requested_limit)

    @staticmethod
    def _target_list(value: Any) -> list[str]:
        if value in (None, "", []):
            return []
        values = value if isinstance(value, list) else [value]
        targets: list[str] = []
        for item in values:
            target = str(item).strip()
            if target and target not in targets:
                targets.append(target)
        return targets

    @staticmethod
    def _compound_target_limit(
        *,
        requested_limit: int | None,
        raw_limit: Any,
        target_count: int,
    ) -> int | None:
        if requested_limit is not None:
            return requested_limit
        try:
            total_limit = int(raw_limit)
        except (TypeError, ValueError):
            return None
        if total_limit <= target_count:
            return 1
        return max(1, (total_limit + target_count - 1) // target_count)

    @staticmethod
    def _extract_requested_limit(user_message: str) -> int | None:
        if any(term in user_message for term in ("一个", "一道", "一份", "一款", "一家")):
            return 1
        match = COUNT_PATTERN.search(user_message)
        if match:
            return max(1, int(match.group(1)))
        return None

    @staticmethod
    def _merge_list_filter(filters: dict[str, Any], key: str, value: Any) -> None:
        if value in (None, "", []):
            return
        incoming = value if isinstance(value, list) else [value]
        existing = list(filters.get(key) or [])
        for item in incoming:
            if item not in existing:
                existing.append(item)
        filters[key] = existing

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes"}:
                return True
            if normalized in {"false", "0", "no"}:
                return False
        return bool(value)

    @staticmethod
    def _clean_json(raw: str) -> str:
        text = raw.strip()
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start : end + 1]
        return text

    def _rule_plan(self, user_message: str, context: dict[str, Any] | None = None) -> AgentPlan:
        message = user_message.strip().lower()
        context = context or {}

        if message in {"hi", "hello", "你好", "嗨", "在吗"}:
            return AgentPlan(intent="greeting", should_answer_directly=True)

        if any(term in message for term in ("撤回", "恢复", "刚才那个不要", "undo")):
            return AgentPlan(
                intent="undo_action",
                tool_calls=[GraphToolCall(tool_name="undo_last_action", writes_database=True)],
                should_answer_directly=True,
            )

        if "购物车" in message and any(term in message for term in ("清空", "删除全部", "全部删除")):
            return AgentPlan(
                intent="cart_action",
                tool_calls=[GraphToolCall(tool_name="cart_clear", writes_database=True)],
                should_answer_directly=True,
            )

        if "购物车" in message and any(term in message for term in ("加", "添加", "放入", "加入")):
            # Try last_recommendations first, then fall back to recent_evidence
            last_recs = context.get("last_recommendations", [])
            if not last_recs:
                # Extract dish_ids from recent_evidence (populated after RAG)
                last_recs = [
                    {"dish_id": e.get("facts", {}).get("dish_id")}
                    for e in context.get("recent_evidence", [])
                    if e.get("source_type") == "dish" and e.get("facts", {}).get("dish_id")
                ]
            if last_recs:
                items = [
                    {"dish_id": rec["dish_id"], "quantity": 1}
                    for rec in last_recs
                    if rec.get("dish_id")
                ]
                if items:
                    return AgentPlan(
                        intent="cart_action",
                        tool_calls=[GraphToolCall(
                            tool_name="add_to_cart",
                            arguments={"items": items},
                            writes_database=True,
                        )],
                        should_answer_directly=True,
                    )
            # No recommendations or evidence available — need RAG first
            return AgentPlan(
                intent="cart_action",
                normalized_query=user_message,
                requires_rag=True,
                tool_calls=[GraphToolCall(
                    tool_name="recommend_dishes",
                    arguments={"query": user_message},
                    writes_database=False,
                )],
                should_answer_directly=True,
            )

        if "购物车" in message and any(term in message for term in ("删", "移除", "去掉", "不要")):
            return AgentPlan(
                intent="cart_action",
                tool_calls=[GraphToolCall(tool_name="remove_from_cart", writes_database=True)],
                should_answer_directly=True,
            )

        if any(term in message for term in ("保存地址", "加入地址", "地址管理")):
            return AgentPlan(
                intent="address_action",
                tool_calls=[GraphToolCall(tool_name="save_address", writes_database=True)],
                should_answer_directly=True,
            )

        if any(term in message for term in ("偏好", "记住我", "不吃", "过敏")):
            return AgentPlan(
                intent="preference_action",
                tool_calls=[GraphToolCall(tool_name="upsert_preference", writes_database=True)],
                should_answer_directly=True,
            )

        if any(term in message for term in ("推荐", "吃什么", "来几个")):
            filters = {
                "cuisine_types": ["湘菜"] if "湘菜" in user_message else [],
                "flavor_preferences": ["辣"] if "辣" in user_message else [],
                "budget_max": None,
                "party_size": None,
                "exclude_allergens": [],
            }
            return AgentPlan(
                intent="recommendation",
                normalized_query=user_message,
                requires_rag=True,
                filters=filters,
                should_answer_directly=True,
            )

        if any(term in message for term in ("商家", "店", "营业", "电话", "地址", "多少钱", "价格")):
            return AgentPlan(
                intent="knowledge",
                normalized_query=user_message,
                requires_rag=True,
                should_answer_directly=True,
            )

        return AgentPlan(intent="unsupported", should_answer_directly=True)
