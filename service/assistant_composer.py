from service.assistant_models import AssistantCandidate, AssistantParsedQuery


def compose_assistant_response(session_id: str, parsed: AssistantParsedQuery, candidates: list[AssistantCandidate]) -> dict:
    if parsed.needs_clarification:
        return {
            "session_id": session_id,
            "message": parsed.clarification_question,
            "needs_clarification": True,
            "clarification_question": parsed.clarification_question,
            "extracted_constraints": {
                "query_type": parsed.query_type,
                "cuisine_types": parsed.cuisine_types,
                "budget_max": parsed.budget_max,
                "party_size": parsed.party_size,
                "exclude_allergens": parsed.exclude_allergens,
                "comparison_targets": parsed.comparison_targets,
            },
            "recommendations": [],
            "comparisons": [],
            "citations": [],
            "suggested_actions": [],
        }

    recommendations = []
    comparisons = []
    citations = []

    for candidate in candidates:
        citations.append(
            {
                "source_type": candidate.source_type,
                "source_id": candidate.source_id,
                "title": candidate.citation_title,
                "snippet": candidate.citation_snippet,
            }
        )
        if candidate.source_type == "dish":
            recommendations.append(
                {
                    "source_type": "dish",
                    "merchant_id": candidate.merchant_id,
                    "merchant_name": candidate.merchant_name,
                    "dish_id": candidate.dish_id,
                    "dish_name": candidate.dish_name,
                    "price": candidate.price,
                    "reason": f"匹配{candidate.reason_facts[0]}偏好，单价 {candidate.price:.0f} 元，且未命中{candidate.reason_facts[-1].replace('不含', '')}过敏原。",
                }
            )
        else:
            comparisons.append(
                {
                    "merchant_id": candidate.merchant_id,
                    "merchant_name": candidate.merchant_name,
                    "summary": candidate.summary,
                    "highlights": candidate.reason_facts,
                }
            )

    return {
        "session_id": session_id,
        "message": "我根据你提供的条件整理了更匹配的选项。",
        "needs_clarification": False,
        "clarification_question": None,
        "extracted_constraints": {
            "query_type": parsed.query_type,
            "cuisine_types": parsed.cuisine_types,
            "budget_max": parsed.budget_max,
            "party_size": parsed.party_size,
            "exclude_allergens": parsed.exclude_allergens,
            "comparison_targets": parsed.comparison_targets,
        },
        "recommendations": recommendations,
        "comparisons": comparisons,
        "citations": citations,
        "suggested_actions": ["查看商家详情", "继续补充口味偏好"],
    }
