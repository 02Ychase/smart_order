import json
import logging
import os
from typing import Literal

from service.assistant_models import AssistantCandidate
from service.constraint_resolver import ResolvedConstraints
from tools.llm_tool import call_llm

logger = logging.getLogger(__name__)


_RESPONDER_PROMPT = """你是一个智能点餐助手的回复生成器。

用户消息：{user_message}
意图类型：{intent}

以下是你检索到的证据信息：
{evidence_text}

请根据以上证据，生成一段自然语言回复，并严格按照以下 JSON 格式返回，不要包含任何其他文字：

{{
    "message": "给用户的自然语言回复",
    "suggested_actions": ["建议的下一步操作1", "建议的下一步操作2"]
}}

要求：
- 回复要自然、亲切、有信息量
- 必须基于提供的证据，不要编造
- 如果是推荐，说明推荐理由
- 如果是比较，突出差异点
- 如果是知识问答，直接回答关键信息

记住：只返回纯 JSON，不要有任何额外字符和解释。"""


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
        tool_results: list[dict] | None = None,
    ) -> dict:
        if intent == "greeting":
            return {
                "message": "你好！我是你的智能点餐助手，可以帮你推荐菜品、比较商家，或者回答关于餐厅的问题。",
                "response_type": "greeting",
                "needs_clarification": False,
                "clarification_question": None,
                "extracted_constraints": None,
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": ["推荐几种川菜", "比较两家商家"],
            }

        if intent == "action_intent":
            return {
                "message": "我已经理解你的意图，但该功能将在下一阶段开放。",
                "response_type": "action_pending",
                "needs_clarification": False,
                "clarification_question": None,
                "extracted_constraints": None,
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": [],
            }

        if intent == "unsupported":
            return {
                "message": "抱歉，我暂时还无法处理这个请求。你可以问我关于菜品推荐、商家比较或餐厅信息的问题。",
                "response_type": "unsupported",
                "needs_clarification": False,
                "clarification_question": None,
                "extracted_constraints": None,
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": [],
            }

        # Build structured data regardless of LLM success
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

        # Try LLM generation if model is available
        if self._model_name and evidence:
            try:
                llm_result = self._generate_with_llm(intent, user_message, evidence)
                return {
                    "message": llm_result.get("message", ""),
                    "response_type": response_type,
                    "needs_clarification": False,
                    "clarification_question": None,
                    "extracted_constraints": None,
                    "recommendations": recommendations,
                    "comparisons": comparisons,
                    "citations": citations,
                    "suggested_actions": llm_result.get("suggested_actions", []),
                }
            except Exception as e:
                logger.warning(f"LLM response generation failed: {e}, falling back to template")

        # Fallback template
        message = "我根据你提供的条件整理了更匹配的选项。"
        if intent == "knowledge":
            message = "根据我查到的信息："

        return {
            "message": message,
            "response_type": response_type,
            "needs_clarification": False,
            "clarification_question": None,
            "extracted_constraints": None,
            "recommendations": recommendations,
            "comparisons": comparisons,
            "citations": citations,
            "suggested_actions": ["查看更多详情"] if recommendations else [],
        }

    def _generate_with_llm(self, intent: str, user_message: str, evidence: list[AssistantCandidate]) -> dict:
        evidence_text = self._format_evidence(evidence)
        prompt = _RESPONDER_PROMPT.format(
            user_message=user_message,
            intent=intent,
            evidence_text=evidence_text,
        )
        llm_response = call_llm(query=prompt, system_instruction="")

        cleaned = self._clean_json_response(llm_response)
        return json.loads(cleaned)

    @staticmethod
    def _format_evidence(evidence: list[AssistantCandidate]) -> str:
        lines = []
        for i, candidate in enumerate(evidence, 1):
            if candidate.source_type == "dish":
                lines.append(
                    f"{i}. 菜品：{candidate.dish_name}（{candidate.merchant_name}）"
                    f" - 价格：{candidate.price}元"
                    f" - 特色：{candidate.summary}"
                    f" - 匹配原因：{', '.join(candidate.reason_facts)}"
                )
            else:
                lines.append(
                    f"{i}. 商家：{candidate.merchant_name}"
                    f" - 简介：{candidate.summary}"
                    f" - 亮点：{', '.join(candidate.reason_facts)}"
                )
        return "\n".join(lines)

    @staticmethod
    def _clean_json_response(raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return raw[start : end + 1]
        return raw
