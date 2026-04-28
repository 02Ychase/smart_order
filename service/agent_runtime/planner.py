from __future__ import annotations

import json
import os
from typing import Any

from service.agent_runtime.prompts import PromptRegistry
from service.agent_runtime.state import AgentPlan, GraphToolCall
from tools.llm_tool import call_llm


class LangGraphAgentPlanner:
    def __init__(self, prompts: PromptRegistry | None = None) -> None:
        self.prompts = prompts or PromptRegistry()
        self._model_name = os.getenv("MODEL_NAME")
        self._llm = None

    def plan(self, user_message: str, context: dict[str, Any]) -> AgentPlan:
        if self._llm is not None:
            try:
                raw = self._llm.call(user_message, self.prompts.load("agent.planner"))
                return self._parse(raw)
            except Exception:
                return self._rule_plan(user_message)

        if self._model_name:
            try:
                raw = call_llm(
                    query=json.dumps({"message": user_message, "context": context}, ensure_ascii=False),
                    system_instruction=self.prompts.load("agent.planner"),
                )
                return self._parse(raw)
            except Exception:
                return self._rule_plan(user_message)

        return self._rule_plan(user_message)

    def _parse(self, raw: str | dict[str, Any]) -> AgentPlan:
        parsed = raw if isinstance(raw, dict) else json.loads(self._clean_json(raw))
        filters = {
            "cuisine_types": [],
            "flavor_preferences": [],
            "budget_max": None,
            "party_size": None,
            "exclude_allergens": [],
        }
        filters.update(parsed.get("filters") or {})
        return AgentPlan(
            intent=parsed.get("intent", "unsupported"),
            normalized_query=parsed.get("normalized_query", ""),
            requires_rag=self._parse_bool(parsed.get("requires_rag", False)),
            filters=filters,
            tool_calls=[
                GraphToolCall(
                    tool_name=item.get("tool_name", ""),
                    arguments=item.get("arguments", {}),
                    writes_database=self._parse_bool(item.get("writes_database", False)),
                )
                for item in parsed.get("tool_calls") or []
            ],
            should_answer_directly=self._parse_bool(parsed.get("should_answer_directly", True)),
            response_hint=parsed.get("response_hint", ""),
        )

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

    def _rule_plan(self, user_message: str) -> AgentPlan:
        message = user_message.strip().lower()

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
