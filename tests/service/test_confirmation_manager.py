from datetime import datetime, timedelta, timezone

from service.agent_state import AssistantTurnState, PendingAction
from service.confirmation_manager import ConfirmationManager


def test_recommendation_cart_action_requires_confirmation() -> None:
    manager = ConfirmationManager()
    assert manager.requires_confirmation(
        action_type="cart_add",
        payload={"source": "recommendation", "items": [{"dish_id": 11, "quantity": 1}]},
    ) is True


def test_explicit_unique_small_cart_action_can_execute_directly() -> None:
    manager = ConfirmationManager()
    assert manager.requires_confirmation(
        action_type="cart_add",
        payload={
            "source": "explicit",
            "items": [{"dish_id": 11, "quantity": 1}],
            "unique_match": True,
        },
    ) is False


def test_address_save_requires_confirmation() -> None:
    manager = ConfirmationManager()
    assert manager.requires_confirmation(
        action_type="address_save",
        payload={"label": "家", "contact_phone": "13800000000"},
    ) is True


def test_store_and_consume_pending_action() -> None:
    manager = ConfirmationManager()
    state = AssistantTurnState(session_id="s1", user_id=1)
    action = PendingAction(
        action_type="cart_add",
        summary="加入购物车",
        payload={"items": [{"dish_id": 11, "quantity": 1}]},
        requires_user_id=True,
    )

    manager.store_pending_action(state, action)
    consumed = manager.consume_pending_action(state, user_message="确认")

    assert consumed is action
    assert state.pending_action is None


def test_expired_pending_action_is_not_consumed() -> None:
    manager = ConfirmationManager()
    expired = PendingAction(
        action_type="cart_add",
        summary="过期动作",
        payload={"items": [{"dish_id": 11, "quantity": 1}]},
        requires_user_id=True,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    state = AssistantTurnState(session_id="s1", pending_action=expired)

    consumed = manager.consume_pending_action(state, user_message="确认")

    assert consumed is None
    assert state.pending_action is None
