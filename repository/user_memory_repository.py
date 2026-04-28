from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.user_memory import UserMemory


class UserMemoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_for_user(self, user_id: int) -> list[UserMemory]:
        statement = (
            select(UserMemory)
            .where(UserMemory.user_id == user_id, UserMemory.status == "active")
            .order_by(UserMemory.updated_at.desc(), UserMemory.id.desc())
        )
        return list(self.session.scalars(statement))

    def upsert(
        self,
        user_id: int,
        memory_type: str,
        content: str,
        confidence: float,
    ) -> UserMemory:
        statement = select(UserMemory).where(
            UserMemory.user_id == user_id,
            UserMemory.memory_type == memory_type,
            UserMemory.content == content,
            UserMemory.status == "active",
        )
        record = self.session.scalar(statement)
        if record is None:
            record = UserMemory(
                user_id=user_id,
                memory_type=memory_type,
                content=content,
                confidence=confidence,
            )
            self.session.add(record)
        else:
            record.confidence = confidence
            record.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(record)
        return record
