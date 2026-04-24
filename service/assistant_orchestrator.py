from __future__ import annotations

from service.agent_planner import AgentPlanner
from service.agent_state import EvidencePack, PendingAction, ToolResult
from service.assistant_session_store import InMemoryAssistantSessionStore
from service.confirmation_manager import ConfirmationManager
from service.grounded_responder import GroundedResponder
from service.tool_registry import ToolRegistry, ToolSchema
from service.tools.address_tool import commit_address_action_tool, parse_address_tool
from service.tools.cart_tool import commit_cart_action_tool
from service.tools.catalog_tool import search_catalog_tool
from service.tools.recommendation_tool import recommend_dishes_tool


class AssistantOrchestrator:
    def __init__(
        self,
        session,
        session_store: InMemoryAssistantSessionStore | None = None,
        planner: AgentPlanner | None = None,
        tool_registry=None,
        confirmation_manager: ConfirmationManager | None = None,
        responder: GroundedResponder | None = None,
    ) -> None:
        self.session = session
        self.session_store = session_store or InMemoryAssistantSessionStore()
        self.planner = planner or AgentPlanner()
        self.confirmation_manager = confirmation_manager or ConfirmationManager()
        self.responder = responder or GroundedResponder()
        self.tool_registry = tool_registry or self._build_registry()

    def _build_registry(self):
        registry = ToolRegistry()
        registry.register(
            ToolSchema("search_catalog", "Search catalog", {"type": "object"}),
            lambda **kwargs: search_catalog_tool(session=self.session, **kwargs),
        )
        registry.register(
            ToolSchema("recommend_dishes", "Recommend dishes", {"type": "object"}),
            lambda **kwargs: recommend_dishes_tool(session=self.session, **kwargs),
        )
        registry.register(
            ToolSchema("commit_cart_action", "Commit cart action", {"type": "object"}, side_effect="direct_write"),
            lambda **kwargs: commit_cart_action_tool(session=self.session, **kwargs),
        )
        registry.register(
            ToolSchema("parse_address", "Parse address", {"type": "object"}),
            lambda **kwargs: parse_address_tool(**kwargs),
        )
        registry.register(
            ToolSchema("commit_address_action", "Commit address action", {"type": "object"}, side_effect="direct_write"),
            lambda **kwargs: commit_address_action_tool(session=self.session, **kwargs),
        )
        return registry

    def chat(self, *, message: str, session_id: str | None, user_id: int | None = None) -> dict:
        state = self.session_store.get_or_create(session_id, user_id=user_id)

        pending = self.confirmation_manager.consume_pending_action(state, message)
        if pending is not None:
            return self._commit_pending_action(state.session_id, user_id, pending)

        decision = self.planner.plan(
            message,
            session_context={
                "slots": state.slots,
                "pending_action": state.pending_action.action_type if state.pending_action else None,
            },
        )

        if decision.intent == "greeting":
            return self._base_response(state.session_id, "你好！我是你的智能点餐助手。", "greeting")

        if decision.intent == "unsupported":
            return self._base_response(state.session_id, "抱歉，我暂时还无法处理这个请求。", "unsupported")

        if decision.missing_slots:
            return self._base_response(
                state.session_id,
                decision.clarification_question or "请补充预算、人数或口味偏好。",
                "clarification",
                needs_clarification=True,
                clarification_question=decision.clarification_question,
            )

        tool_results = []
        evidence: list[EvidencePack] = []
        for call in decision.tool_plan:
            result = self.tool_registry.execute(call.tool_name, call.arguments)
            tool_results.append(result)
            if isinstance(result, ToolResult):
                evidence.extend(result.evidence)

        if decision.intent == "address_action" and tool_results:
            first = tool_results[0]
            if isinstance(first, ToolResult) and not first.ok:
                message = first.error.message if first.error else "地址信息不完整，请补充。"
                return self._base_response(state.session_id, message, "clarification", needs_clarification=True)
            if isinstance(first, ToolResult):
                address = first.data["address"]
                action = PendingAction(
                    action_type="address_save",
                    summary=f"保存地址：{address['city']}{address['district']}{address['detail_address']}",
                    payload={"address": address},
                    requires_user_id=True,
                )
                self.confirmation_manager.store_pending_action(state, action)
                return {
                    **self._base_response(state.session_id, f"{action.summary}，是否确认？", "confirmation_required"),
                    "pending_action": self._serialize_pending_action(action),
                }

        if decision.intent == "mixed_task" and tool_results:
            cart_items = []
            for result in tool_results:
                if isinstance(result, ToolResult):
                    cart_items.extend(result.data.get("cart_candidate_items", []))
            action = PendingAction(
                action_type="cart_add",
                summary=f"将 {len(cart_items)} 道推荐菜加入购物车",
                payload={"items": cart_items, "source": "recommendation"},
                requires_user_id=True,
            )
            self.confirmation_manager.store_pending_action(state, action)
            return self._recommendation_response(
                state.session_id,
                evidence,
                response_type="confirmation_required",
                pending_action=action,
            )

        if decision.intent in {"recommendation", "knowledge"}:
            return self._recommendation_response(
                state.session_id,
                evidence,
                response_type="recommendation" if decision.intent == "recommendation" else "knowledge",
            )

        return self._base_response(state.session_id, "我已理解你的请求，请补充更多细节。", "clarification")

    def _commit_pending_action(self, session_id: str, user_id: int | None, pending: PendingAction) -> dict:
        if pending.requires_user_id and user_id is None:
            return self._base_response(session_id, "请先登录后再执行该操作。", "clarification")

        if pending.action_type == "cart_add":
            result = self.tool_registry.execute(
                "commit_cart_action",
                {"user_id": user_id, "items": pending.payload["items"]},
            )
            return {
                **self._base_response(session_id, "操作已完成。", "action_completed"),
                "executed_actions": [{
                    "type": "cart_add",
                    "success": bool(result.get("success")),
                    "message": pending.summary,
                    "data": result,
                }],
            }

        if pending.action_type == "address_save":
            result = self.tool_registry.execute(
                "commit_address_action",
                {"user_id": user_id, "address": pending.payload["address"]},
            )
            return {
                **self._base_response(session_id, "地址已保存。", "action_completed"),
                "executed_actions": [{
                    "type": "address_save",
                    "success": True,
                    "message": pending.summary,
                    "data": result,
                }],
            }

        return self._base_response(session_id, "暂不支持该确认动作。", "unsupported")

    def _recommendation_response(
        self,
        session_id: str,
        evidence: list[EvidencePack],
        response_type: str,
        pending_action: PendingAction | None = None,
    ) -> dict:
        recommendations = [
            {
                "source_type": item.source_type,
                "merchant_id": item.merchant_id,
                "merchant_name": item.facts.get("merchant_name", item.title),
                "dish_id": item.facts.get("dish_id") if item.source_type == "dish" else None,
                "dish_name": item.facts.get("dish_name") if item.source_type == "dish" else None,
                "price": item.facts.get("price") if item.source_type == "dish" else None,
                "reason": "、".join(item.why_matched),
            }
            for item in evidence
        ]
        citations = [
            {
                "source_type": item.source_type,
                "source_id": item.source_id,
                "title": item.title,
                "snippet": item.citation,
            }
            for item in evidence
        ]
        message = "我根据你的需求找到了这些结果。"
        if pending_action:
            message = f"{message} {pending_action.summary}，是否确认？"
        return {
            **self._base_response(session_id, message, response_type),
            "recommendations": recommendations,
            "citations": citations,
            "pending_action": self._serialize_pending_action(pending_action),
        }

    def _base_response(
        self,
        session_id: str,
        message: str,
        response_type: str,
        needs_clarification: bool = False,
        clarification_question: str | None = None,
    ) -> dict:
        return {
            "session_id": session_id,
            "message": message,
            "response_type": response_type,
            "needs_clarification": needs_clarification,
            "clarification_question": clarification_question,
            "extracted_constraints": None,
            "recommendations": [],
            "comparisons": [],
            "citations": [],
            "suggested_actions": [],
            "pending_action": None,
            "executed_actions": [],
        }

    def _serialize_pending_action(self, pending_action: PendingAction | None) -> dict | None:
        if pending_action is None:
            return None
        return {
            "action_id": pending_action.action_id,
            "type": pending_action.action_type,
            "summary": pending_action.summary,
            "items": pending_action.payload.get("items", []),
        }
