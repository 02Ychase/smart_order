from __future__ import annotations

import json
import logging
import os
from typing import Any

from service.agent_state import AgentDecision, ToolCall
from tools.llm_tool import call_llm

logger = logging.getLogger(__name__)


PLANNER_PROMPT = """你是 smart_order 的智能点餐 Agent Planner。
你只能返回 JSON，不要返回 Markdown。

可用工具：
- search_catalog: 查询商家和菜品事实
- recommend_dishes: 基于预算、人数、口味、过敏原推荐菜品
- prepare_cart_action: 准备加入购物车动作，不直接写库
- parse_address: 从自然语言中解析地址字段
- prepare_address_action: 准备保存地址动作，不直接写库

意图必须是：
greeting, knowledge, recommendation, cart_action, address_action, mixed_task, unsupported

返回格式：
{
  "intent": "...",
  "reasoning_summary": "...",
  "tool_plan": [{"tool": "...", "arguments": {}, "requires_confirmation": false}],
  "missing_slots": [],
  "clarification_question": null,
  "needs_confirmation": false
}

关键规则：
- 查询有哪些店、多少钱、营业时间属于 knowledge。
- 个性化推荐如果缺少预算或人数，应填 missing_slots 并给 clarification_question。
- 推荐后加入购物车属于 mixed_task，需要先推荐，再准备确认动作。
- 保存地址属于 address_action，保存前需要确认。
"""


class AgentPlanner:
    def __init__(self) -> None:
        self._model_name = os.getenv("MODEL_NAME")
        self._llm = None

    def plan(self, user_message: str, session_context: dict[str, Any]) -> AgentDecision:
        if self._llm is not None:
            raw = self._llm.call(user_message, PLANNER_PROMPT)
            return self._parse_decision(raw)

        if self._model_name:
            try:
                raw = call_llm(
                    query=json.dumps(
                        {"message": user_message, "session_context": session_context},
                        ensure_ascii=False,
                    ),
                    system_instruction=PLANNER_PROMPT,
                )
                return self._parse_decision(raw)
            except Exception as exc:
                logger.warning("planner LLM failed, using rules: %s", exc)

        return self._rule_plan(user_message)

    def _parse_decision(self, raw: str | dict[str, Any]) -> AgentDecision:
        parsed = raw if isinstance(raw, dict) else json.loads(self._clean_json(raw))
        return AgentDecision(
            intent=parsed.get("intent", "unsupported"),
            reasoning_summary=parsed.get("reasoning_summary", ""),
            tool_plan=[
                ToolCall(
                    tool_name=item.get("tool", ""),
                    arguments=item.get("arguments", {}),
                    requires_confirmation=bool(item.get("requires_confirmation", False)),
                )
                for item in parsed.get("tool_plan", [])
            ],
            missing_slots=list(parsed.get("missing_slots", [])),
            clarification_question=parsed.get("clarification_question"),
            needs_confirmation=bool(parsed.get("needs_confirmation", False)),
        )

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

    def _rule_plan(self, user_message: str) -> AgentDecision:
        msg = user_message.strip().lower()
        if msg in {"hi", "hello", "你好", "嗨", "在吗"}:
            return AgentDecision(intent="greeting", reasoning_summary="问候")

        if "地址" in msg and any(word in msg for word in ("保存", "加入", "添加", "地址管理")):
            return AgentDecision(
                intent="address_action",
                reasoning_summary="保存地址",
                tool_plan=[ToolCall(tool_name="parse_address", arguments={"message": user_message})],
                needs_confirmation=True,
            )

        if "购物车" in msg or "加一份" in msg or "加入" in msg:
            if "推荐" in msg:
                return AgentDecision(
                    intent="mixed_task",
                    reasoning_summary="推荐后加购",
                    missing_slots=["budget", "party_size"],
                    clarification_question="请告诉我这顿几个人吃、预算多少？",
                    needs_confirmation=True,
                )
            return AgentDecision(
                intent="cart_action",
                reasoning_summary="明确加购",
                tool_plan=[ToolCall(tool_name="search_catalog", arguments={"query": user_message})],
            )

        if "推荐" in msg or "吃什么" in msg:
            return AgentDecision(
                intent="recommendation",
                reasoning_summary="个性化推荐",
                missing_slots=["budget", "party_size"],
                clarification_question="请告诉我这顿几个人吃、预算多少？",
            )

        if any(word in msg for word in ("有哪些", "有什么", "几点", "营业", "多少钱", "价格", "电话")):
            return AgentDecision(
                intent="knowledge",
                reasoning_summary="查询信息",
                tool_plan=[ToolCall(tool_name="search_catalog", arguments={"query": user_message})],
            )

        return AgentDecision(intent="unsupported", reasoning_summary="无法识别")
