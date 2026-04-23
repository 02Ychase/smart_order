import json
import logging
import os
from dataclasses import dataclass
from typing import Literal

from tools.llm_tool import call_llm

logger = logging.getLogger(__name__)


@dataclass
class RoutingResult:
    intent: Literal["greeting", "recommendation", "comparison", "knowledge", "action_intent", "unsupported"]
    requires_retrieval: bool
    likely_needs_clarification: bool = False
    future_tool: str | None = None


_INTENT_ROUTER_PROMPT = """你是一个智能点餐助手的意图分类器。

请分析用户输入的意图，并严格按照以下 JSON 格式返回，不要包含任何其他文字：

{
    "intent": "意图类型",
    "requires_retrieval": true/false,
    "likely_needs_clarification": true/false,
    "future_tool": "工具名称或null"
}

意图类型必须是以下之一：
- greeting: 打招呼、问候（如"你好"、"Hi"、"在吗"）
- recommendation: 推荐菜品或商家（如"推荐川菜"、"吃什么好"）
- comparison: 比较多个商家或菜品（如"比较A和B"、"A和B哪个好"）
- knowledge: 查询具体信息（如"几点营业"、"电话多少"、"多少钱"）
- action_intent: 执行操作意图（如"加入购物车"、"添加地址"、"下单"）
- unsupported: 无法处理的请求

requires_retrieval: 是否需要检索数据库（recommendation/comparison/knowledge 需要）
likely_needs_clarification: 用户意图是否缺少关键信息需要澄清
future_tool: 如果是 action_intent，填写工具名（add_to_cart/save_address/checkout），否则填 null

正确示例：
用户："你好" -> {"intent": "greeting", "requires_retrieval": false, "likely_needs_clarification": false, "future_tool": null}
用户："推荐几种川菜" -> {"intent": "recommendation", "requires_retrieval": true, "likely_needs_clarification": true, "future_tool": null}
用户："帮我加入购物车" -> {"intent": "action_intent", "requires_retrieval": false, "likely_needs_clarification": false, "future_tool": "add_to_cart"}
用户："比较兰姨小炒和午后豆房" -> {"intent": "comparison", "requires_retrieval": true, "likely_needs_clarification": false, "future_tool": null}

记住：只返回纯 JSON，不要有任何额外字符和解释。"""


class IntentRouter:
    def __init__(self) -> None:
        self._model_name = os.getenv("MODEL_NAME")

    def route(self, message: str) -> RoutingResult:
        if self._model_name:
            try:
                return self._route_with_llm(message)
            except Exception as e:
                logger.warning(f"LLM intent routing failed: {e}, falling back to rules")

        return self._route_with_rules(message)

    def _route_with_llm(self, message: str) -> RoutingResult:
        llm_response = call_llm(query=message, system_instruction=_INTENT_ROUTER_PROMPT)

        cleaned = self._clean_json_response(llm_response)
        parsed = json.loads(cleaned)

        return RoutingResult(
            intent=parsed["intent"],
            requires_retrieval=parsed.get("requires_retrieval", False),
            likely_needs_clarification=parsed.get("likely_needs_clarification", False),
            future_tool=parsed.get("future_tool"),
        )

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

    def _route_with_rules(self, message: str) -> RoutingResult:
        msg = message.strip().lower()

        if msg in ("hi", "hello", "你好", "在吗", "嗨"):
            return RoutingResult("greeting", requires_retrieval=False)

        if "加入购物车" in msg or "添加地址" in msg or "保存地址" in msg:
            tool = "add_to_cart" if "购物车" in msg else "save_address"
            return RoutingResult("action_intent", requires_retrieval=False, future_tool=tool)

        if any(w in msg for w in ("对比", "比较", "vs", "versus")):
            return RoutingResult("comparison", requires_retrieval=True)

        if any(w in msg for w in ("推荐", "吃什么", "适合", "推荐菜", "推荐商家")):
            return RoutingResult("recommendation", requires_retrieval=True)

        if any(w in msg for w in ("几点", "营业", "电话", "地址", "多少钱", "价格", "口味", "配料")):
            return RoutingResult("knowledge", requires_retrieval=True)

        return RoutingResult("unsupported", requires_retrieval=False)
