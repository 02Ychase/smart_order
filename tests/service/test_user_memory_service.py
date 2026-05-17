from service.user_memory_service import UserMemoryService


class InMemoryRepo:
    def __init__(self):
        self.records = []

    def list_for_user(self, user_id, limit=100):
        results = [
            record
            for record in self.records
            if record["user_id"] == user_id and record["status"] == "active"
        ]
        return results[:limit]

    def list_for_user_by_types(self, user_id, memory_types):
        return [
            record
            for record in self.records
            if (
                record["user_id"] == user_id
                and record["status"] == "active"
                and record["memory_type"] in memory_types
            )
        ]

    def list_for_user_excluding_types(self, user_id, memory_types, limit=100):
        results = [
            record
            for record in self.records
            if (
                record["user_id"] == user_id
                and record["status"] == "active"
                and record["memory_type"] not in memory_types
            )
        ]
        return results[:limit]

    def upsert(self, user_id, memory_type, content, confidence):
        for record in self.records:
            if (
                record["user_id"] == user_id
                and record["memory_type"] == memory_type
                and record["content"] == content
            ):
                record["confidence"] = confidence
                return record
        record = {
            "id": len(self.records) + 1,
            "user_id": user_id,
            "memory_type": memory_type,
            "content": content,
            "confidence": confidence,
            "status": "active",
        }
        self.records.append(record)
        return record


def test_user_memory_upserts_structured_preference() -> None:
    service = UserMemoryService(repository=InMemoryRepo())

    memory = service.upsert_memory(
        9,
        "food_preference",
        "prefers spicy Hunan dishes",
        0.9,
    )

    assert memory["memory_type"] == "food_preference"
    assert service.list_memories(9)[0]["content"] == "prefers spicy Hunan dishes"


def test_user_memory_upsert_updates_existing_fact_confidence() -> None:
    service = UserMemoryService(repository=InMemoryRepo())

    first = service.upsert_memory(9, "food_preference", "prefers spicy Hunan dishes", 0.7)
    second = service.upsert_memory(9, "food_preference", "prefers spicy Hunan dishes", 0.95)

    assert first["id"] == second["id"]
    assert service.list_memories(9)[0]["confidence"] == 0.95
