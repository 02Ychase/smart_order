from unittest.mock import patch

from service.agent_runtime.prompts import PromptRegistry


# ── existing tests ────────────────────────────────────────────────

def test_prompt_registry_loads_planner_prompt() -> None:
    registry = PromptRegistry()

    prompt = registry.load("agent.planner")

    assert "smart_order" in prompt
    assert "should_answer_directly" in prompt
    assert "结构化格式" in prompt
    assert "recommend_dishes" in prompt
    assert "search_catalog" in prompt
    assert "禁止编造工具名" in prompt


def test_prompt_registry_rejects_unknown_prompt_key() -> None:
    registry = PromptRegistry()

    try:
        registry.load("agent.missing")
    except KeyError as exc:
        assert "agent.missing" in str(exc)
    else:
        raise AssertionError("unknown prompt key should raise KeyError")


# ── caching tests ─────────────────────────────────────────────────

def test_cache_populated_after_first_load() -> None:
    PromptRegistry.clear_cache()
    registry = PromptRegistry()

    assert PromptRegistry.cache_info()["size"] == 0

    registry.load("agent.planner")

    info = PromptRegistry.cache_info()
    assert info["size"] == 1
    assert "agent.planner" in info["keys"]


def test_subsequent_loads_return_cached_content() -> None:
    PromptRegistry.clear_cache()
    registry = PromptRegistry()

    first = registry.load("agent.planner")
    second = registry.load("agent.planner")

    assert first == second
    assert PromptRegistry.cache_info()["size"] == 1


def test_cache_is_shared_across_instances() -> None:
    PromptRegistry.clear_cache()
    reg_a = PromptRegistry()
    reg_b = PromptRegistry()

    reg_a.load("agent.planner")
    info = PromptRegistry.cache_info()
    assert info["size"] == 1

    result = reg_b.load("agent.planner")
    assert "smart_order" in result
    assert PromptRegistry.cache_info()["size"] == 1


def test_clear_cache_removes_all_entries() -> None:
    PromptRegistry.clear_cache()
    registry = PromptRegistry()

    registry.load("agent.planner")
    registry.load("agent.memory_writer")
    assert PromptRegistry.cache_info()["size"] == 2

    PromptRegistry.clear_cache()
    assert PromptRegistry.cache_info()["size"] == 0
    assert PromptRegistry.cache_info()["keys"] == []


def test_different_keys_have_different_cached_values() -> None:
    PromptRegistry.clear_cache()
    registry = PromptRegistry()

    planner = registry.load("agent.planner")
    memory = registry.load("agent.memory_writer")

    assert planner != memory
    assert "smart_order" in planner
    assert PromptRegistry.cache_info()["size"] == 2


def test_cache_avoids_disk_read_on_second_load() -> None:
    PromptRegistry.clear_cache()
    registry = PromptRegistry()

    # First load hits disk
    first = registry.load("agent.planner")

    # Second load should NOT read from disk — patch Path.read_text to detect
    with patch("pathlib.Path.read_text") as mock_read:
        second = registry.load("agent.planner")
        mock_read.assert_not_called()

    assert first == second


def test_unknown_key_not_cached() -> None:
    PromptRegistry.clear_cache()
    registry = PromptRegistry()

    try:
        registry.load("agent.missing")
    except KeyError:
        pass

    assert PromptRegistry.cache_info()["size"] == 0


def test_cache_info_returns_accurate_size() -> None:
    PromptRegistry.clear_cache()
    registry = PromptRegistry()

    assert PromptRegistry.cache_info()["size"] == 0

    keys = ["agent.planner", "agent.memory_writer", "agent.undo_resolver"]
    for k in keys:
        registry.load(k)

    assert PromptRegistry.cache_info()["size"] == len(keys)
    for k in keys:
        assert k in PromptRegistry.cache_info()["keys"]
