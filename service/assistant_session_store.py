from uuid import uuid4

from service.agent_state import AssistantTurnState, PendingAction
from service.assistant_models import AssistantParsedQuery


class InMemoryAssistantSessionStore:
    def __init__(self) -> None:
        self._store: dict[str, AssistantTurnState] = {}

    def get_or_create(self, session_id: str | None, user_id: int | None = None) -> AssistantTurnState:
        actual_session_id = session_id or uuid4().hex
        state = self._store.get(actual_session_id)
        if state is None:
            state = AssistantTurnState(session_id=actual_session_id, user_id=user_id)
            self._store[actual_session_id] = state
        elif user_id is not None:
            state.user_id = user_id
        return state

    def update_agent_state(
        self,
        *,
        session_id: str,
        user_id: int | None = None,
        last_intent: str | None = None,
        slots: dict | None = None,
        last_evidence_ids: list[str] | None = None,
        pending_action: PendingAction | None = None,
    ) -> AssistantTurnState:
        state = self._store[session_id]
        if user_id is not None:
            state.user_id = user_id
        if last_intent is not None:
            state.last_intent = last_intent
        if slots:
            state.slots.update(slots)
        if last_evidence_ids is not None:
            state.last_evidence_ids = last_evidence_ids
        if pending_action is not None:
            state.pending_action = pending_action
        return state

    def update(
        self,
        session_id: str,
        user_message: str,
        parsed_query: AssistantParsedQuery | None,
        candidate_ids: list[int],
    ) -> AssistantTurnState:
        return self.update_agent_state(
            session_id=session_id,
            last_evidence_ids=[str(item) for item in candidate_ids],
        )
