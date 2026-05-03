from __future__ import annotations

from service.agent_runtime.state import AgentPlan
from service.rag.models import RagQueryPlan


class RagQueryPlanner:
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

        _apply_memory_hints(memories, cuisine_types, flavor_preferences, exclude_allergens)

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
        )


def _apply_memory_hints(
    memories: list[dict],
    cuisine_types: list[str],
    flavor_preferences: list[str],
    exclude_allergens: list[str],
) -> None:
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
