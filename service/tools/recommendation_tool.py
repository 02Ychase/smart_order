from __future__ import annotations

from service.agent_state import ToolResult
from service.rag_retriever import RagRetriever


def recommend_dishes_tool(
    query: str,
    budget: float | None = None,
    party_size: int | None = None,
    exclude_allergens: list[str] | None = None,
    limit: int = 3,
    session=None,
    _retriever=None,
) -> ToolResult:
    retriever = _retriever or RagRetriever(session=session)
    message_parts = [query]
    if party_size:
        message_parts.append(f"{party_size}个人")
    if budget:
        message_parts.append(f"{budget}元以内")
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
