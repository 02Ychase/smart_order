from __future__ import annotations

from repository.user_memory_repository import UserMemoryRepository
from service.config import get_config

# Safety-critical memory types that must always be loaded in full.
# If a future "on-demand recall" mechanism is introduced, these types
# must be exempted and loaded unconditionally to prevent missing
# allergen / dietary constraints.
ALWAYS_LOAD_TYPES: frozenset[str] = frozenset({"dietary_constraint"})


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
        limit = get_config().memory.max_memories_per_user
        always_records = self.repository.list_for_user_by_types(user_id, ALWAYS_LOAD_TYPES)
        remaining_limit = max(0, int(limit) - len(always_records))
        other_records = self.repository.list_for_user_excluding_types(
            user_id,
            ALWAYS_LOAD_TYPES,
            limit=remaining_limit,
        )
        return [self._serialize(record) for record in [*always_records, *other_records]]

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
