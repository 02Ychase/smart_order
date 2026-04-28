from __future__ import annotations

from service.agent_runtime.state import AgentPlan
from service.agent_state import EvidencePack, ToolResult
from service.rag.retriever import AdvancedRagRetriever


def _to_legacy_evidence(item):
    if isinstance(item, EvidencePack):
        return item
    return EvidencePack(
        source_type=item.source_type,
        source_id=item.source_id,
        merchant_id=item.merchant_id,
        title=item.title,
        facts=item.facts,
        why_matched=item.why_matched,
        citation=item.citation,
        score=item.score,
    )


def recommend_dishes_tool(
    query: str = "",
    budget: float | None = None,
    budget_max: float | None = None,
    party_size: int | None = None,
    cuisine: str | None = None,
    cuisine_type: str | None = None,
    preferences: str | None = None,
    exclude_allergens: list[str] | None = None,
    premium: bool = False,
    limit: int = 3,
    session=None,
    _retriever=None,
    **_: object,
) -> ToolResult:
    retriever = _retriever or AdvancedRagRetriever(session=session)
    message_parts = [query] if query else []
    cuisine_value = cuisine or cuisine_type
    if cuisine_value:
        message_parts.append(cuisine_value)
    if preferences:
        message_parts.append(preferences)
    if party_size:
        message_parts.append(f"{party_size}个人")
    budget_value = budget if budget is not None else budget_max
    if budget_value:
        message_parts.append(f"{budget_value}元以内")
    for allergen in exclude_allergens or []:
        message_parts.append(f"不要{allergen}")

    full_message = "，".join(message_parts)
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query=full_message,
        requires_rag=True,
        filters={
            "cuisine_types": [cuisine_value] if cuisine_value else [],
            "flavor_preferences": [preferences] if preferences else [],
            "budget_max": budget_value,
            "party_size": party_size,
            "exclude_allergens": exclude_allergens or [],
        },
    )
    try:
        rag_evidence = retriever.retrieve(full_message, agent_plan=agent_plan, memories=[], limit=int(limit or 3))
    except TypeError:
        rag_evidence = retriever.retrieve(full_message, limit=limit)
    evidence = [_to_legacy_evidence(item) for item in rag_evidence]
    premium_requested = premium or any(term in "，".join(message_parts) for term in ("比较贵", "越贵越好", "无预算", "无上限"))
    if premium_requested:
        evidence = sorted(
            evidence,
            key=lambda item: float(item.facts.get("price") or 0),
            reverse=True,
        )
    cart_items = [
        {"dish_id": item.source_id, "quantity": 1}
        for item in evidence
        if item.source_type == "dish"
    ]
    return ToolResult.ok_result(
        tool_name="recommend_dishes",
        data={
            "count": len(evidence),
            "cart_candidate_items": cart_items,
        },
        evidence=evidence,
    )
