import os
from typing import Literal

from service.assistant_models import AssistantCandidate
from service.constraint_resolver import ResolvedConstraints


class GroundedResponder:
    def __init__(self) -> None:
        self._model_name = os.getenv("MODEL_NAME")

    def respond(
        self,
        *,
        intent: Literal["recommendation", "comparison", "knowledge", "greeting", "action_intent", "unsupported"],
        user_message: str,
        constraints: ResolvedConstraints | None,
        evidence: list[AssistantCandidate],
        session_context: list[dict],
    ) -> dict:
        if intent == "greeting":
            return {
                "message": "你好！我是你的智能点餐助手，可以帮你推荐菜品、比较商家，或者回答关于餐厅的问题。",
                "response_type": "greeting",
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": ["推荐几种川菜", "比较两家商家"],
            }

        if intent == "action_intent":
            return {
                "message": "我已经理解你的意图，但该功能将在下一阶段开放。",
                "response_type": "action_pending",
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": [],
            }

        if intent == "unsupported":
            return {
                "message": "抱歉，我暂时还无法处理这个请求。你可以问我关于菜品推荐、商家比较或餐厅信息的问题。",
                "response_type": "unsupported",
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": [],
            }

        # For recommendation/comparison/knowledge: build evidence-grounded response
        # TODO: integrate LLM generation in future step
        recommendations = []
        comparisons = []
        citations = []

        for candidate in evidence:
            if candidate.source_type == "dish":
                recommendations.append({
                    "source_type": candidate.source_type,
                    "merchant_id": candidate.merchant_id,
                    "merchant_name": candidate.merchant_name,
                    "dish_id": candidate.dish_id,
                    "dish_name": candidate.dish_name,
                    "price": candidate.price,
                    "reason": f"匹配{', '.join(candidate.reason_facts)}。",
                })
            else:
                comparisons.append({
                    "merchant_id": candidate.merchant_id,
                    "merchant_name": candidate.merchant_name,
                    "summary": candidate.summary,
                    "highlights": candidate.reason_facts,
                })

            citations.append({
                "source_type": candidate.source_type,
                "source_id": candidate.source_id,
                "title": candidate.citation_title,
                "snippet": candidate.citation_snippet,
            })

        response_type = "recommendation" if intent == "recommendation" else "comparison" if intent == "comparison" else "knowledge"

        message = "我根据你提供的条件整理了更匹配的选项。"
        if intent == "knowledge":
            message = "根据我查到的信息："

        return {
            "message": message,
            "response_type": response_type,
            "recommendations": recommendations,
            "comparisons": comparisons,
            "citations": citations,
            "suggested_actions": ["查看更多详情"] if recommendations else [],
        }
