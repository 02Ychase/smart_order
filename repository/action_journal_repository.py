from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.action_journal import ActionJournal


class ActionJournalRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, **kwargs) -> ActionJournal:
        record = ActionJournal(**kwargs)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def find_last_undoable(self, user_id: int) -> ActionJournal | None:
        statement = (
            select(ActionJournal)
            .where(
                ActionJournal.user_id == user_id,
                ActionJournal.status == "completed",
                ActionJournal.undo_policy != "not_undoable",
            )
            .order_by(ActionJournal.id.desc())
        )
        return self.session.scalar(statement)

    def mark_undone(self, action_id: str) -> ActionJournal | None:
        statement = select(ActionJournal).where(ActionJournal.action_id == action_id)
        record = self.session.scalar(statement)
        if record is None:
            return None
        record.status = "undone"
        self.session.commit()
        self.session.refresh(record)
        return record
