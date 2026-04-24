from __future__ import annotations

from typing import Any

from service.agent_state import AssistantTurnState, PendingAction


CONFIRM_MESSAGES = {"确认", "好的", "可以", "是", "yes", "ok", "加吧", "保存吧"}
CANCEL_MESSAGES = {"取消", "不要", "算了", "否", "no", "cancel"}


class ConfirmationManager:
    def requires_confirmation(self, action_type: str, payload: dict[str, Any]) -> bool:
        if action_type == "address_save":
            return True

        if action_type != "cart_add":
            return True

        if payload.get("source") == "recommendation":
            return True

        if not payload.get("unique_match", False):
            return True

        items = payload.get("items", [])
        if len(items) != 1:
            return True

        quantity = int(items[0].get("quantity", 0))
        return quantity < 1 or quantity > 3

    def store_pending_action(self, state: AssistantTurnState, action: PendingAction) -> PendingAction:
        state.pending_action = action
        return action

    def consume_pending_action(self, state: AssistantTurnState, user_message: str) -> PendingAction | None:
        normalized = user_message.strip().lower()
        pending = state.pending_action
        if pending is None:
            return None

        if pending.is_expired():
            state.pending_action = None
            return None

        if normalized in CANCEL_MESSAGES:
            state.pending_action = None
            return None

        if normalized in CONFIRM_MESSAGES:
            state.pending_action = None
            return pending

        return None

    def is_confirmation_message(self, user_message: str) -> bool:
        return user_message.strip().lower() in CONFIRM_MESSAGES
