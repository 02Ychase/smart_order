from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str = ""
    category: str = ""  # "safety" | "off_topic" | ""


class InputGuardrail:
    INJECTION_PATTERNS = [
        r"忽略.{0,10}(?:之前|以上|所有).{0,10}(?:指令|提示|规则)",
        r"(?:tell|show|reveal|display).{0,20}(?:system|prompt|instruction)",
        r"ignore.{0,20}(?:previous|above|all).{0,20}(?:instructions?|rules?|prompts?)",
        r"你(?:的|是).{0,10}(?:系统|提示词|指令)",
    ]

    OFF_TOPIC_PATTERNS = [
        r"(?:天气|气温|下雨|晴天|台风|暴雨)",
        r"(?:作文|论文|翻译|写.{0,4}文章|写.{0,4}报告)",
        r"(?:数学|方程|计算|微积分|几何)",
        r"(?:代码|编程|bug|python|java|javascript)",
        r"(?:新闻|股票|基金|比特币|炒股)",
        r"(?:唱歌|讲笑话|写诗|写故事|写小说)",
        r"(?:考试|作业|高考|公务员)",
    ]

    # Food/ordering context words — if any of these appear alongside an
    # off-topic keyword, the message is likely a legitimate ordering request
    # phrased with casual context (e.g. "下雨天推荐几个热乎的川菜").
    FOOD_CONTEXT_PATTERNS = [
        r"(?:吃|菜|餐|饭|外卖|点餐|推荐|商家|店|购物车|下单|配送)",
        r"(?:辣|甜|酸|咸|麻|清淡|口味)",
        r"(?:川菜|湘菜|粤菜|火锅|烧烤|小吃|夜宵|早餐|午餐|晚餐)",
        r"(?:价格|多少钱|便宜|贵|预算)",
    ]

    def __init__(self, max_length: int = 500, enable_topic_check: bool = True) -> None:
        self._max_length = max_length
        self._enable_topic_check = enable_topic_check
        self._injection_patterns = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]
        self._off_topic_patterns = [re.compile(p, re.IGNORECASE) for p in self.OFF_TOPIC_PATTERNS]
        self._food_context_patterns = [re.compile(p) for p in self.FOOD_CONTEXT_PATTERNS]

    def check(self, message: str) -> GuardrailResult:
        # Tier 1: safety checks (always run)
        if len(message) > self._max_length:
            return GuardrailResult(
                allowed=False,
                reason=f"input length {len(message)} exceeds max {self._max_length}",
                category="safety",
            )

        for pattern in self._injection_patterns:
            if pattern.search(message):
                return GuardrailResult(
                    allowed=False,
                    reason="potential prompt injection detected",
                    category="safety",
                )

        # Tier 2: topic relevance check (can be disabled)
        if self._enable_topic_check and self._is_off_topic(message):
            return GuardrailResult(
                allowed=False,
                reason="off-topic request not related to food ordering",
                category="off_topic",
            )

        return GuardrailResult(allowed=True)

    def _is_off_topic(self, message: str) -> bool:
        """Return True only if the message hits an off-topic pattern AND
        does not contain any food/ordering context words (exemption)."""
        has_off_topic = any(p.search(message) for p in self._off_topic_patterns)
        if not has_off_topic:
            return False
        has_food_context = any(p.search(message) for p in self._food_context_patterns)
        return not has_food_context


class OutputGuardrail:
    PRICE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*元")

    def check(self, response: str, evidence: list[dict]) -> GuardrailResult:
        evidence_prices = set()
        for item in evidence:
            facts = item.get("facts", {})
            price = facts.get("price")
            if price is not None:
                evidence_prices.add(float(price))

        if evidence_prices:
            response_prices = {float(m.group(1)) for m in self.PRICE_PATTERN.finditer(response)}
            hallucinated = response_prices - evidence_prices
            if hallucinated:
                return GuardrailResult(
                    allowed=False,
                    reason=f"potential price hallucination: {hallucinated} not in evidence",
                )

        return GuardrailResult(allowed=True)
