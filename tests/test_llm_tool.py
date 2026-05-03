import json
import os
from unittest.mock import MagicMock, patch

from tools.llm_tool import (
    _create_repair_prompt,
    _validate_json,
    call_llm,
    call_llm_with_retry,
)


class FakeResponse:
    """Fake LLM response with a `.content` attribute."""

    def __init__(self, content: str):
        self.content = content


def _mock_chain(content: str):
    """Create a MagicMock chain whose `.invoke()` returns a FakeResponse."""
    chain = MagicMock()
    chain.invoke.return_value = FakeResponse(content)
    return chain


# ---------------------------------------------------------------------------
# _validate_json
# ---------------------------------------------------------------------------


def test_validate_json_valid_object() -> None:
    assert _validate_json('{"key": "value"}')


def test_validate_json_valid_array() -> None:
    assert _validate_json('[1, 2, 3]')


def test_validate_json_valid_nested() -> None:
    assert _validate_json('{"a": {"b": [1, 2]}}')


def test_validate_json_invalid_missing_brace() -> None:
    assert not _validate_json('{"key": "value"')


def test_validate_json_invalid_plain_text() -> None:
    assert not _validate_json("hello world")


def test_validate_json_invalid_trailing_comma() -> None:
    assert not _validate_json('{"key": "value",}')


# ---------------------------------------------------------------------------
# _create_repair_prompt
# ---------------------------------------------------------------------------


def test_create_repair_prompt_includes_original_and_error() -> None:
    prompt = _create_repair_prompt('{"bad json', "Expecting value")
    assert '{"bad json' in prompt
    assert "Expecting value" in prompt
    assert "corrected JSON" in prompt


# ---------------------------------------------------------------------------
# call_llm — success on first attempt
# ---------------------------------------------------------------------------


@patch.dict(os.environ, {"MODEL_NAME": "gpt-4o-mini"})
@patch("tools.llm_tool.init_chat_model")
def test_call_llm_success_first_attempt_no_json(mock_init: MagicMock) -> None:
    mock_init.return_value = MagicMock()
    with patch("tools.llm_tool.ChatPromptTemplate") as mock_template:
        mock_template.from_messages.return_value = _mock_chain("Hello, world!")
        result = call_llm("Hi", "You are a helpful assistant")
    assert result == "Hello, world!"
    # Called once — no retries.
    assert mock_init.call_count == 1


@patch.dict(os.environ, {"MODEL_NAME": "gpt-4o-mini"})
@patch("tools.llm_tool.init_chat_model")
def test_call_llm_success_first_attempt_with_valid_json(mock_init: MagicMock) -> None:
    mock_init.return_value = MagicMock()
    with patch("tools.llm_tool.ChatPromptTemplate") as mock_template:
        mock_template.from_messages.return_value = _mock_chain('{"intent": "greeting"}')
        result = call_llm("Hi", "You are a JSON assistant")
    assert result == '{"intent": "greeting"}'
    assert mock_init.call_count == 1


# ---------------------------------------------------------------------------
# call_llm — retry on JSON validation failure
# ---------------------------------------------------------------------------


@patch.dict(os.environ, {"MODEL_NAME": "gpt-4o-mini"})
@patch("tools.llm_tool.init_chat_model")
@patch("tools.llm_tool.time.sleep")
def test_call_llm_retry_and_recover_on_json_validation(
    mock_sleep: MagicMock, mock_init: MagicMock
) -> None:
    mock_init.return_value = MagicMock()

    # First response: malformed JSON; second response: valid JSON.
    chain1 = _mock_chain("not valid json at all")
    chain2 = _mock_chain('{"intent": "recommendation"}')

    with patch("tools.llm_tool.ChatPromptTemplate") as mock_template:
        mock_template.from_messages.side_effect = [chain1, chain2]
        result = call_llm(
            "recommend dishes",
            "Return JSON with intent field",
        )

    assert result == '{"intent": "recommendation"}'
    assert mock_init.call_count == 2
    mock_sleep.assert_called_once()  # backoff before retry


@patch.dict(os.environ, {"MODEL_NAME": "gpt-4o-mini"})
@patch("tools.llm_tool.init_chat_model")
@patch("tools.llm_tool.time.sleep")
def test_call_llm_json_validation_exhausts_retries(
    mock_sleep: MagicMock, mock_init: MagicMock
) -> None:
    mock_init.return_value = MagicMock()

    chain = _mock_chain("always invalid")

    with patch("tools.llm_tool.ChatPromptTemplate") as mock_template:
        mock_template.from_messages.return_value = chain
        try:
            call_llm("query", "JSON output please", max_retries=2)
        except json.JSONDecodeError:
            pass
        else:
            raise AssertionError("Expected JSONDecodeError")

    # 1 initial + 2 retries = 3 total attempts
    assert mock_init.call_count == 3
    assert mock_sleep.call_count == 2


# ---------------------------------------------------------------------------
# call_llm — retry on API / generic errors
# ---------------------------------------------------------------------------


@patch.dict(os.environ, {"MODEL_NAME": "gpt-4o-mini"})
@patch("tools.llm_tool.init_chat_model")
@patch("tools.llm_tool.time.sleep")
def test_call_llm_retry_on_api_error_then_succeed(
    mock_sleep: MagicMock, mock_init: MagicMock
) -> None:
    mock_init.return_value = MagicMock()

    chain_fail = MagicMock()
    chain_fail.invoke.side_effect = RuntimeError("API timeout")
    chain_ok = _mock_chain("recovered")

    with patch("tools.llm_tool.ChatPromptTemplate") as mock_template:
        mock_template.from_messages.side_effect = [chain_fail, chain_ok]
        result = call_llm("Hi", "You are a helpful assistant")

    assert result == "recovered"
    assert mock_init.call_count == 2
    mock_sleep.assert_called_once()


@patch.dict(os.environ, {"MODEL_NAME": "gpt-4o-mini"})
@patch("tools.llm_tool.init_chat_model")
@patch("tools.llm_tool.time.sleep")
def test_call_llm_raises_after_max_retries(
    mock_sleep: MagicMock, mock_init: MagicMock
) -> None:
    mock_init.return_value = MagicMock()

    chain = MagicMock()
    chain.invoke.side_effect = ConnectionError("network unreachable")

    with patch("tools.llm_tool.ChatPromptTemplate") as mock_template:
        mock_template.from_messages.return_value = chain
        try:
            call_llm("Hi", "System prompt", max_retries=1)
        except ConnectionError:
            pass
        else:
            raise AssertionError("Expected ConnectionError")

    # 1 initial + 1 retry = 2 attempts
    assert mock_init.call_count == 2
    assert mock_sleep.call_count == 1


# ---------------------------------------------------------------------------
# call_llm — no JSON validation when system_instruction lacks json keyword
# ---------------------------------------------------------------------------


@patch.dict(os.environ, {"MODEL_NAME": "gpt-4o-mini"})
@patch("tools.llm_tool.init_chat_model")
def test_call_llm_skips_json_validation_for_plain_prompt(mock_init: MagicMock) -> None:
    """Non-JSON prompts should return content as-is, even if it isn't valid JSON."""
    mock_init.return_value = MagicMock()
    with patch("tools.llm_tool.ChatPromptTemplate") as mock_template:
        mock_template.from_messages.return_value = _mock_chain(
            "This is not JSON at all"
        )
        result = call_llm("Hello", "You are a friendly chatbot")
    assert result == "This is not JSON at all"
    assert mock_init.call_count == 1


# ---------------------------------------------------------------------------
# call_llm — raises ValueError when MODEL_NAME is missing
# ---------------------------------------------------------------------------


@patch.dict(os.environ, {}, clear=True)
def test_call_llm_raises_valueerror_without_model_name() -> None:
    # Also remove MODEL_NAME completely
    with patch.dict(os.environ, {}, clear=True):
        try:
            call_llm("Hello", "You are a bot")
        except ValueError as e:
            assert "模型配置信息不全" in str(e)
        else:
            raise AssertionError("Expected ValueError")


# ---------------------------------------------------------------------------
# call_llm_with_retry
# ---------------------------------------------------------------------------


@patch.dict(os.environ, {"MODEL_NAME": "gpt-4o-mini"})
@patch("tools.llm_tool.init_chat_model")
def test_call_llm_with_retry_delegates_to_call_llm(mock_init: MagicMock) -> None:
    mock_init.return_value = MagicMock()
    with patch("tools.llm_tool.ChatPromptTemplate") as mock_template:
        mock_template.from_messages.return_value = _mock_chain("ok")
        result = call_llm_with_retry("q", "sys")
    assert result == "ok"
    # call_llm is called once (succeeds on first attempt)
    assert mock_init.call_count == 1


@patch.dict(os.environ, {"MODEL_NAME": "gpt-4o-mini"})
@patch("tools.llm_tool.init_chat_model")
@patch("tools.llm_tool.time.sleep")
def test_call_llm_with_retry_passes_max_retries(
    mock_sleep: MagicMock, mock_init: MagicMock
) -> None:
    mock_init.return_value = MagicMock()

    chain = MagicMock()
    chain.invoke.side_effect = RuntimeError("fail")

    with patch("tools.llm_tool.ChatPromptTemplate") as mock_template:
        mock_template.from_messages.return_value = chain
        try:
            call_llm_with_retry("q", "sys", max_retries=1)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Expected RuntimeError")

    # 1 initial + 1 retry = 2
    assert mock_init.call_count == 2


# ---------------------------------------------------------------------------
# call_llm — exponential backoff
# ---------------------------------------------------------------------------


@patch.dict(os.environ, {"MODEL_NAME": "gpt-4o-mini"})
@patch("tools.llm_tool.init_chat_model")
@patch("tools.llm_tool.time.sleep")
def test_call_llm_exponential_backoff_delays(
    mock_sleep: MagicMock, mock_init: MagicMock
) -> None:
    mock_init.return_value = MagicMock()

    chain = MagicMock()
    chain.invoke.side_effect = [
        RuntimeError("fail 1"),
        RuntimeError("fail 2"),
        _mock_chain("finally ok").invoke.side_effect,
    ]

    with patch("tools.llm_tool.ChatPromptTemplate") as mock_template:
        # Each call to from_messages creates a new template; chain is the same mock.
        # We just return the same chain object each time.
        mock_template.from_messages.return_value = chain
        call_llm("q", "sys", max_retries=3, retry_delay=1.5)

    assert mock_sleep.call_count == 2
    # First retry delay: 1.5 * (2^0) = 1.5
    # Second retry delay: 1.5 * (2^1) = 3.0
    mock_sleep.assert_any_call(1.5)
    mock_sleep.assert_any_call(3.0)
