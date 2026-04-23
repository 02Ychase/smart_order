import os
from dataclasses import dataclass
from typing import Literal


@dataclass
class RoutingResult:
    intent: Literal["greeting", "recommendation", "comparison", "knowledge", "action_intent", "unsupported"]
    requires_retrieval: bool
    likely_needs_clarification: bool = False
    future_tool: str | None = None


class IntentRouter:
    def __init__(self) -> None:
        self._model_name = os.getenv("MODEL_NAME")

    def route(self, message: str) -> RoutingResult:
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
