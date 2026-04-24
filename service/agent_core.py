import json
import logging
import os
from dataclasses import dataclass

from tools.llm_tool import call_llm

logger = logging.getLogger(__name__)


@dataclass
class AgentDecision:
    reasoning: str
    intent: str  # greeting | knowledge | recommendation | action | unsupported
    needs_clarification: bool = False
    clarification_question: str | None = None
    tool_calls: list[dict] = None
    search_query: str | None = None

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


_AGENT_DECISION_PROMPT = """你是一个智能点餐助手的决策中枢。请分析用户输入，决定如何处理。

可用工具：
1. search_knowledge_base(query, filters?) - 搜索商家/菜品知识，用于查询类问题
2. recommend_dishes(budget?, party_size?, preferences?) - 个性化推荐
3. add_to_cart(dish_id, quantity=1) - 加入购物车
4. save_address(label, detail_address, contact_phone) - 保存地址

请按以下JSON格式返回，只返回JSON：
{
    "reasoning": "你的思考过程",
    "intent": "意图类型",
    "needs_clarification": true/false,
    "clarification_question": "如果需要澄清的问题，否则null",
    "tool_calls": [{"name": "工具名", "parameters": {}}] 或 [],
    "search_query": "优化后的搜索关键词或null"
}

意图类型：
- greeting: 问候（你好/Hi）
- knowledge: 查询信息（有什么店/多少钱/几点营业）- 不需要预算和人数
- recommendation: 个性化推荐（帮我选菜/吃什么好）- 需要预算和人数
- action: 执行操作（加购物车/保存地址）
- unsupported: 无法处理

关键区分：
- "推荐几个卖咖啡的店" → knowledge（查询有哪些店，不是个性化推荐）
- "推荐几个川菜，3个人预算200" → recommendation（有约束的个性化推荐）
- "推荐几个川菜" → recommendation + needs_clarification（缺少约束）
"""


class AgentCore:
    def __init__(self) -> None:
        self._model_name = os.getenv("MODEL_NAME")
        self._llm = None

    def _call_llm(self, query: str) -> dict:
        # Allow test injection via self._llm
        if self._llm is not None:
            return self._llm.call(query, _AGENT_DECISION_PROMPT)

        if not self._model_name:
            logger.warning("MODEL_NAME not set, falling back to rule-based")
            return self._rule_based_decide(query)

        try:
            llm_response = call_llm(query=query, system_instruction=_AGENT_DECISION_PROMPT)
            cleaned = self._clean_json_response(llm_response)
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"LLM decision failed: {e}, falling back to rules")
            return self._rule_based_decide(query)

    @staticmethod
    def _clean_json_response(raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return raw[start : end + 1]
        return raw

    def _rule_based_decide(self, query: str) -> dict:
        msg = query.strip().lower()

        if msg in ("hi", "hello", "你好", "在吗", "嗨"):
            return {"reasoning": "问候", "intent": "greeting", "needs_clarification": False, "tool_calls": []}

        if any(w in msg for w in ("加入购物车", "添加地址", "保存地址")):
            tool = "add_to_cart" if "购物车" in msg else "save_address"
            return {"reasoning": "操作意图", "intent": "action", "needs_clarification": False, "tool_calls": [{"name": tool, "parameters": {}}]}

        if any(w in msg for w in ("对比", "比较", "vs", "versus")):
            return {"reasoning": "比较", "intent": "knowledge", "needs_clarification": False, "tool_calls": [{"name": "search_knowledge_base", "parameters": {"query": query}}]}

        if any(w in msg for w in ("几点", "营业", "电话", "地址", "多少钱", "价格", "口味", "配料", "有哪些", "有什么", "卖", "店")):
            return {"reasoning": "查询信息", "intent": "knowledge", "needs_clarification": False, "tool_calls": [{"name": "search_knowledge_base", "parameters": {"query": query}}]}

        if "推荐" in msg or "吃什么" in msg or "适合" in msg:
            return {"reasoning": "个性化推荐但缺少约束", "intent": "recommendation", "needs_clarification": True, "clarification_question": "请告诉我这顿大概几个人吃、预算多少？", "tool_calls": []}

        return {"reasoning": "无法识别", "intent": "unsupported", "needs_clarification": False, "tool_calls": []}

    def decide(self, user_message: str) -> AgentDecision:
        result = self._call_llm(user_message)

        return AgentDecision(
            reasoning=result.get("reasoning", ""),
            intent=result.get("intent", "unsupported"),
            needs_clarification=result.get("needs_clarification", False),
            clarification_question=result.get("clarification_question"),
            tool_calls=result.get("tool_calls", []),
            search_query=result.get("search_query"),
        )
