from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str = ""


class InputGuardrail:
    INJECTION_PATTERNS = [
        r"忽略.{0,10}(?:之前|以上|所有).{0,10}(?:指令|提示|规则)",
        r"(?:tell|show|reveal|display).{0,20}(?:system|prompt|instruction)",
        r"ignore.{0,20}(?:previous|above|all).{0,20}(?:instructions?|rules?|prompts?)",
        r"你(?:的|是).{0,10}(?:系统|提示词|指令)",
    ]

    def __init__(self, max_length: int = 500) -> None:
        self._max_length = max_length
        self._patterns = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]

    def check(self, message: str) -> GuardrailResult:
        if len(message) > self._max_length:
            return GuardrailResult(allowed=False, reason=f"input length {len(message)} exceeds max {self._max_length}")

        for pattern in self._patterns:
            if pattern.search(message):
                return GuardrailResult(allowed=False, reason="potential prompt injection detected")

        return GuardrailResult(allowed=True)


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
