import pytest

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
