from __future__ import annotations

from repository.user_memory_repository import UserMemoryRepository


class UserMemoryService:
    def __init__(self, session=None, repository=None) -> None:
        self.repository = repository or UserMemoryRepository(session)

    def _serialize(self, record) -> dict:
        if isinstance(record, dict):
            return dict(record)
        return {
            "id": record.id,
            "user_id": record.user_id,
            "memory_type": record.memory_type,
            "content": record.content,
            "confidence": record.confidence,
            "status": record.status,
        }

    def list_memories(self, user_id: int) -> list[dict]:
        return [self._serialize(record) for record in self.repository.list_for_user(user_id)]

    def upsert_memory(
        self,
        user_id: int,
        memory_type: str,
        content: str,
        confidence: float,
    ) -> dict:
        return self._serialize(
            self.repository.upsert(user_id, memory_type, content, confidence)
        )
