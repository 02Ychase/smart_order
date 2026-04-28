from __future__ import annotations


def upsert_preference_tool(
    user_id: int,
    memory_type: str,
    content: str,
    session=None,
    _memory_service=None,
) -> dict:
    service = _memory_service
    if service is None:
        from service.user_memory_service import UserMemoryService

        service = UserMemoryService(session)

    before_snapshot = service.list_memories(user_id)
    memory = service.upsert_memory(
        user_id=user_id,
        memory_type=memory_type,
        content=content,
        confidence=1.0,
    )
    after_snapshot = service.list_memories(user_id)
    return {
        "success": True,
        "memory": memory,
        "before_snapshot": before_snapshot,
        "after_snapshot": after_snapshot,
        "undo_policy": "snapshot_restore",
        "undo_tool": "restore_user_memory_snapshot",
        "natural_summary": "更新用户偏好",
    }
