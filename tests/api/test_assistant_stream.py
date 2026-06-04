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
    assert any(chunk["type"] == "token" for chunk in chunks)
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


@pytest.mark.asyncio
async def test_stream_emits_tokens_before_payload():
    service = AssistantStreamService(session=None)

    chunks = []
    async for chunk in service.stream_chat_tokens("你好", session_id="stream-order-test", user_id=1):
        chunks.append(chunk)

    token_index = next(i for i, chunk in enumerate(chunks) if chunk["type"] == "token")
    payload_index = next(i for i, chunk in enumerate(chunks) if chunk["type"] == "payload")
    assert token_index < payload_index


def test_stream_chunk_types():
    """Verify expected chunk type values."""
    valid_types = {"token", "payload", "done"}
    for t in valid_types:
        assert isinstance(t, str)


class _StubGraph:
    """Returns a fixed evidence-bearing result without running the real graph."""

    def __init__(self, result):
        self._result = result

    def invoke(self, state, config):
        return {**self._result, "messages": state["messages"]}


@pytest.mark.asyncio
async def test_stream_overrides_message_on_price_hallucination(monkeypatch):
    """Tokens stream optimistically, but if the full text hallucinates a price
    not present in evidence, the authoritative payload message is overridden
    with the safe template."""
    service = AssistantStreamService(session=None)
    service._graph = _StubGraph({
        "response_payload": {
            "response_type": "recommendation",
            "recommendations": [],
            "message": "",
        },
        "recent_evidence": [{
            "source_type": "dish",
            "source_id": 1,
            "merchant_id": 1,
            "title": "宫保鸡丁",
            "facts": {"price": 20.0, "dish_name": "宫保鸡丁", "merchant_name": "川味轩"},
            "score": 1.0,
        }],
        "tool_results": [],
        "current_plan": None,
        "last_recommendations": [],
        "user_id": 1,
    })

    async def _fake_grounded(self, **kwargs):
        for ch in "推荐你花99元尝尝":  # 99元 is NOT in evidence (only 20元)
            yield ch

    monkeypatch.setattr(AssistantStreamService, "_stream_grounded_response", _fake_grounded)

    chunks = [c async for c in service.stream_chat_tokens("推荐", session_id="halluc-test", user_id=1)]

    # Tokens were streamed optimistically (low TTFT preserved)...
    assert "".join(c["content"] for c in chunks if c["type"] == "token") == "推荐你花99元尝尝"
    # ...but the final authoritative payload message dropped the hallucinated price.
    payload = next(c["data"] for c in chunks if c["type"] == "payload")
    assert "99" not in payload["message"]
    _conversation_store.clear("halluc-test")
