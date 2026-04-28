from __future__ import annotations

from uuid import uuid4

from repository.action_journal_repository import ActionJournalRepository


class ActionJournalService:
    def __init__(self, session=None, repository=None) -> None:
        self.repository = repository or ActionJournalRepository(session)

    def record_completed_action(
        self,
        session_id: str,
        user_id: int,
        action_type: str,
        undo_policy: str,
        before_snapshot: dict,
        after_snapshot: dict,
        undo_tool: str,
        natural_summary: str,
    ):
        return self.repository.create(
            action_id=f"act_{uuid4().hex[:12]}",
            session_id=session_id,
            user_id=user_id,
            action_type=action_type,
            status="completed",
            undo_policy=undo_policy,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            undo_tool=undo_tool,
            natural_summary=natural_summary,
        )

    def find_last_undoable(self, user_id: int):
        return self.repository.find_last_undoable(user_id)

    def mark_undone(self, action_id: str):
        return self.repository.mark_undone(action_id)
