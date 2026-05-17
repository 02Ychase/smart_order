from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.user_memory import UserMemory


class UserMemoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_for_user(self, user_id: int, limit: int = 100) -> list[UserMemory]:
        statement = (
            select(UserMemory)
            .where(UserMemory.user_id == user_id, UserMemory.status == "active")
            .order_by(UserMemory.updated_at.desc(), UserMemory.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_for_user_by_types(self, user_id: int, memory_types: set[str] | frozenset[str]) -> list[UserMemory]:
        if not memory_types:
            return []
        statement = (
            select(UserMemory)
            .where(
                UserMemory.user_id == user_id,
                UserMemory.status == "active",
                UserMemory.memory_type.in_(list(memory_types)),
            )
            .order_by(UserMemory.updated_at.desc(), UserMemory.id.desc())
        )
        return list(self.session.scalars(statement))

    def list_for_user_excluding_types(
        self,
        user_id: int,
        memory_types: set[str] | frozenset[str],
        limit: int = 100,
    ) -> list[UserMemory]:
        if limit <= 0:
            return []
        statement = (
            select(UserMemory)
            .where(UserMemory.user_id == user_id, UserMemory.status == "active")
        )
        if memory_types:
            statement = statement.where(UserMemory.memory_type.not_in(list(memory_types)))
        statement = statement.order_by(UserMemory.updated_at.desc(), UserMemory.id.desc()).limit(limit)
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
