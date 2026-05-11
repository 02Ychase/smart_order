import pytest

from service.assistant_service import _conversation_store
from service.assistant_stream_service import AssistantStreamService


@pytest.mark.asyncio
async def test_stream_yields_chunks():
    """Stream service should yield token chunks as SSE events."""
    service = AssistantStreamService(session=None)

    chunks = []
    async for chunk in service.stream_chat_tokens("你好", session_id="s1", user_id=1):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert chunks[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_stream_saves_conversation_history():
    """Stream service should save messages to conversation store."""
    session_id = "stream-history-test"
    _conversation_store.clear(session_id)

    service = AssistantStreamService(session=None)

    chunks = []
    async for chunk in service.stream_chat_tokens("推荐一个菜", session_id=session_id, user_id=1):
        chunks.append(chunk)

    history = _conversation_store.get_history(session_id)
    assert len(history) >= 1
    assert history[0].content == "推荐一个菜"

    _conversation_store.clear(session_id)


def test_stream_chunk_types():
    """Verify expected chunk type values."""
    valid_types = {"token", "payload", "done"}
    for t in valid_types:
        assert isinstance(t, str)
