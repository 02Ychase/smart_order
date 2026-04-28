from __future__ import annotations

from service.agent_runtime.state import AgentPlan
from service.rag.models import RagQueryPlan


class RagQueryPlanner:
    def plan(self, original_query: str, agent_plan: AgentPlan, memories: list[dict]) -> RagQueryPlan:
        normalized = agent_plan.normalized_query or original_query
        filters = agent_plan.filters or {}
        cuisine_types = filters.get("cuisine_types") or []
        flavor_preferences = filters.get("flavor_preferences") or []
        exclude_allergens = filters.get("exclude_allergens") or []
        required_keywords = filters.get("required_keywords") or []
        forbidden_keywords = filters.get("forbidden_keywords") or []

        expansion_queries = [normalized, original_query]
        if "湘菜" in cuisine_types and "辣" in flavor_preferences:
            expansion_queries.append("湘菜 香辣 下饭")
            expansion_queries.append("湖南菜 小炒 剁椒")
        if exclude_allergens:
            expansion_queries.append("不含" + " ".join(exclude_allergens))

        must_filters = {"is_available": True}
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

        source_types = ["dish"]
        if agent_plan.intent == "knowledge":
            source_types = ["dish", "merchant"]
            if any(term in original_query for term in ("店", "商家", "营业", "电话", "地址")):
                source_types = ["merchant"]

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
            },
            source_types=source_types,
            answer_mode=agent_plan.intent,
        )
