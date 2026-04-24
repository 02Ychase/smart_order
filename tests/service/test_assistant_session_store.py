from service.agent_state import PendingAction
from service.assistant_session_store import InMemoryAssistantSessionStore


def test_session_store_tracks_slots_and_pending_action() -> None:
    store = InMemoryAssistantSessionStore()
    state = store.get_or_create("s1", user_id=1)
    action = PendingAction(
        action_type="cart_add",
        summary="加入购物车",
        payload={"items": [{"dish_id": 11, "quantity": 1}]},
        requires_user_id=True,
    )

    store.update_agent_state(
        session_id="s1",
        user_id=1,
        last_intent="mixed_task",
        slots={"budget": 100},
        last_evidence_ids=["dish_11"],
        pending_action=action,
    )
    updated = store.get_or_create("s1")

    assert state is updated
    assert updated.user_id == 1
    assert updated.slots["budget"] == 100
    assert updated.pending_action.action_type == "cart_add"
