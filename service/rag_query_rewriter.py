from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


CUISINE_KEYWORDS = ["川菜", "湘菜", "粤菜", "轻食", "咖啡甜品", "麻辣烫", "披萨意面"]
ALLERGEN_KEYWORDS = ["花生", "麸质", "牛奶", "鸡蛋", "海鲜"]
BUDGET_PATTERN = re.compile(r"(?:预算\s*)?(\d+(?:\.\d+)?)\s*(?:元|块)(?:以内|以下|之内)?")
PARTY_SIZE_PATTERN = re.compile(r"(\d+)\s*(?:个人|人)")


@dataclass
class RagRewriteRequest:
    original_query: str
    semantic_queries: list[str]
    hard_filters: dict
    source_types: list[Literal["dish", "merchant"]] = field(default_factory=lambda: ["dish", "merchant"])


class RagQueryRewriter:
    def rewrite(self, message: str) -> RagRewriteRequest:
        cuisine_types = [item for item in CUISINE_KEYWORDS if item in message]
        exclude_allergens = [
            item
            for item in ALLERGEN_KEYWORDS
            if f"不要{item}" in message or f"不含{item}" in message or f"不能吃{item}" in message
        ]
        budget_match = BUDGET_PATTERN.search(message)
        party_match = PARTY_SIZE_PATTERN.search(message)

        source_types: list[Literal["dish", "merchant"]] = ["dish", "merchant"]
        if any(word in message for word in ("店", "商家", "营业", "电话", "地址")):
            source_types = ["merchant"]

        base_terms = []
        base_terms.extend(cuisine_types)
        if "下饭" in message:
            base_terms.append("下饭")
        if "咖啡" in message:
            base_terms.extend(["咖啡", "甜品", "饮品"])

        semantic_queries = [
            " ".join(base_terms) if base_terms else message,
            message,
        ]
        if cuisine_types and party_match:
            semantic_queries.append(f"{cuisine_types[0]} 适合{party_match.group(1)}人")
        if exclude_allergens:
            semantic_queries.append(f"不含{' '.join(exclude_allergens)}")

        hard_filters = {
            "original_query": message,
            "cuisine_types": cuisine_types,
            "exclude_allergens": exclude_allergens,
            "budget_max": float(budget_match.group(1)) if budget_match else None,
            "party_size": int(party_match.group(1)) if party_match else None,
        }

        return RagRewriteRequest(
            original_query=message,
            semantic_queries=[query for query in semantic_queries if query.strip()],
            hard_filters=hard_filters,
            source_types=source_types,
        )
