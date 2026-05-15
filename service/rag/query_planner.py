from __future__ import annotations

import re

from service.agent_runtime.state import AgentPlan
from service.rag.models import RagQueryPlan


class RagQueryPlanner:
    def __init__(self, rewriter=None) -> None:
        self._rewriter = rewriter

    def plan(self, original_query: str, agent_plan: AgentPlan, memories: list[dict]) -> RagQueryPlan:
        normalized = agent_plan.normalized_query or original_query
        filters = dict(agent_plan.filters or {})

        cuisine_types = list(filters.get("cuisine_types") or [])
        flavor_preferences = list(filters.get("flavor_preferences") or [])
        exclude_allergens = list(filters.get("exclude_allergens") or [])
        required_keywords = list(filters.get("required_keywords") or [])
        forbidden_keywords = list(filters.get("forbidden_keywords") or [])
        source_type_filters = filters.get("source_types") or []
        limit = filters.get("limit")
        sort_by = filters.get("sort_by")
        price_preference = filters.get("price_preference")

        preferred_dishes: list[str] = []
        preferred_merchants: list[str] = []
        _apply_memory_hints(memories, cuisine_types, flavor_preferences, exclude_allergens, preferred_dishes, preferred_merchants)

        if self._rewriter is not None:
            expansion_queries = self._rewriter.rewrite(normalized)
            if original_query not in expansion_queries:
                expansion_queries.append(original_query)
        else:
            expansion_queries = [normalized, original_query]

        if exclude_allergens:
            expansion_queries.append("不含" + " ".join(exclude_allergens))

        must_filters: dict = {"is_available": True}
        if exclude_allergens:
            must_filters["exclude_allergens"] = exclude_allergens
        if cuisine_types:
            must_filters["cuisine_types"] = cuisine_types
        if filters.get("budget_max") is not None:
            must_filters["budget_max"] = filters.get("budget_max")
            must_filters["party_size"] = filters.get("party_size")
        if required_keywords:
            must_filters["required_keywords"] = required_keywords
        if forbidden_keywords:
            must_filters["forbidden_keywords"] = forbidden_keywords
        if filters.get("merchant_name"):
            must_filters["merchant_name"] = filters.get("merchant_name")

        source_types = ["dish"]
        if agent_plan.intent == "knowledge":
            source_types = ["dish", "merchant"]
            if any(term in original_query for term in ("店", "商家", "营业", "电话", "地址")):
                source_types = ["merchant"]
        if source_type_filters:
            source_types = [item for item in source_type_filters if item in {"dish", "merchant"}] or source_types

        return RagQueryPlan(
            original_query=original_query,
            normalized_query=normalized,
            expansion_queries=list(dict.fromkeys(query for query in expansion_queries if query)),
            must_filters=must_filters,
            should_filters={
                "cuisine_types": cuisine_types,
                "flavor_preferences": flavor_preferences,
                "budget_max": filters.get("budget_max"),
                "party_size": filters.get("party_size"),
                "limit": limit,
                "sort_by": sort_by,
                "price_preference": price_preference,
            },
            source_types=source_types,
            answer_mode=agent_plan.intent,
            preferred_dishes=preferred_dishes,
            preferred_merchants=preferred_merchants,
        )


def _apply_memory_hints(
    memories: list[dict],
    cuisine_types: list[str],
    flavor_preferences: list[str],
    exclude_allergens: list[str],
    preferred_dishes: list[str] | None = None,
    preferred_merchants: list[str] | None = None,
) -> None:
    if preferred_dishes is None:
        preferred_dishes = []
    if preferred_merchants is None:
        preferred_merchants = []
    for mem in memories:
        memory_type = mem.get("memory_type", "")
        content = str(mem.get("content", ""))
        if memory_type == "dietary_constraint" and content:
            for allergen in ["花生", "海鲜", "牛奶", "鸡蛋", "小麦", "坚果", "大豆"]:
                if allergen in content and allergen not in exclude_allergens:
                    exclude_allergens.append(allergen)
        elif memory_type == "food_preference" and content:
            for cuisine in ["湘菜", "川菜", "粤菜", "鲁菜", "苏菜", "闽菜", "浙菜", "徽菜", "东北菜"]:
                if cuisine in content and cuisine not in cuisine_types:
                    cuisine_types.append(cuisine)
            for flavor in ["辣", "麻", "酸", "甜", "清淡", "鲜", "香"]:
                if flavor in content and flavor not in flavor_preferences:
                    flavor_preferences.append(flavor)
        elif memory_type == "dish_preference" and content:
            dishes = _extract_dish_preferences(content)
            for dish in dishes:
                if dish not in preferred_dishes:
                    preferred_dishes.append(dish)
        elif memory_type == "merchant_preference" and content:
            merchants = _extract_merchant_preferences(content)
            for merchant in merchants:
                if merchant not in preferred_merchants:
                    preferred_merchants.append(merchant)

    # Also extract dish/merchant preferences from food_preference memories
    # as they may contain specific dish/merchant mentions.
    # Filter out cuisine/flavor descriptions (e.g., "辣的川菜") that are not
    # specific dish names.
    for mem in memories:
        memory_type = mem.get("memory_type", "")
        content = str(mem.get("content", ""))
        if memory_type == "food_preference" and content:
            dishes = _extract_dish_preferences(content)
            for dish in dishes:
                if dish not in preferred_dishes and not _is_cuisine_description(dish):
                    preferred_dishes.append(dish)
            merchants = _extract_merchant_preferences(content)
            for merchant in merchants:
                if merchant not in preferred_merchants:
                    preferred_merchants.append(merchant)


_CUISINE_KEYWORDS = frozenset({
    "湘菜", "川菜", "粤菜", "鲁菜", "苏菜", "闽菜", "浙菜", "徽菜", "东北菜",
    "日料", "韩料", "西餐", "火锅", "烧烤", "甜品", "小吃", "中餐",
})


def _is_cuisine_description(text: str) -> bool:
    """Check if text is a cuisine/flavor description rather than a specific dish name."""
    for kw in _CUISINE_KEYWORDS:
        if text.endswith(kw) and text != kw:
            return True
    return False


def _extract_dish_preferences(content: str) -> list[str]:
    """Extract dish names from memory content."""
    dishes: list[str] = []
    patterns = [
        r"喜欢(?:吃)?(.+?)(?:，|。|,|$)",
        r"爱吃(.+?)(?:，|。|,|$)",
        r"经常点(.+?)(?:，|。|,|$)",
        r"偶尔点(.+?)(?:，|。|,|$)",
        r"推荐(.+?)(?:，|。|,|$)",
        r"想?(?:吃|要)(.+?)(?:，|。|,|$)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content)
        dishes.extend(matches)
    # Split compound dish names joined by connectors
    split_dishes: list[str] = []
    for d in dishes:
        d = d.strip()
        if not d:
            continue
        parts = re.split(r"[和、]|以及|还有", d)
        split_dishes.extend(p.strip() for p in parts if p.strip())
    return split_dishes


def _extract_merchant_preferences(content: str) -> list[str]:
    """Extract merchant names from memory content."""
    merchants: list[str] = []
    patterns = [
        r"经常去(.+?)(?:，|。|,|$)",
        r"喜欢去(.+?)(?:，|。|,|$)",
        r"常去(.+?)(?:，|。|,|$)",
        r"推荐(.+?)(?:，|。|,|$)",
        r"(?:在|去)(.+?)(?:吃|点|买)(?:.+?)?(?:，|。|,|$)?",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content)
        merchants.extend(matches)
    return [m.strip() for m in merchants if m.strip()]
