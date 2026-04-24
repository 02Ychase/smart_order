from __future__ import annotations

from service.agent_state import ToolResult
from service.rag_retriever import RagRetriever


def recommend_dishes_tool(
    query: str = "",
    budget: float | None = None,
    budget_max: float | None = None,
    party_size: int | None = None,
    cuisine: str | None = None,
    cuisine_type: str | None = None,
    preferences: str | None = None,
    exclude_allergens: list[str] | None = None,
    limit: int = 3,
    session=None,
    _retriever=None,
    **_: object,
) -> ToolResult:
    retriever = _retriever or RagRetriever(session=session)
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

    evidence = retriever.retrieve("，".join(message_parts), limit=limit)
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
