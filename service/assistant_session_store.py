from uuid import uuid4

from service.assistant_models import AssistantConversationState, AssistantParsedQuery


class InMemoryAssistantSessionStore:
    def __init__(self) -> None:
        self._store: dict[str, AssistantConversationState] = {}

    def get_or_create(self, session_id: str | None) -> AssistantConversationState:
        actual_session_id = session_id or uuid4().hex
        state = self._store.get(actual_session_id)
        if state is None:
            state = AssistantConversationState(session_id=actual_session_id)
            self._store[actual_session_id] = state
        return state

    def update(
        self,
        session_id: str,
        user_message: str,
        parsed_query: AssistantParsedQuery,
        candidate_ids: list[int],
    ) -> AssistantConversationState:
        state = self._store[session_id]
        state.last_user_message = user_message
        state.parsed_query = parsed_query
        state.candidate_ids = candidate_ids
        return state
