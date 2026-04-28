from service.agent_runtime.prompts import PromptRegistry


def test_prompt_registry_loads_planner_prompt() -> None:
    registry = PromptRegistry()

    prompt = registry.load("agent.planner")

    assert "smart_order" in prompt
    assert "should_answer_directly" in prompt
    assert "只返回" in prompt


def test_prompt_registry_rejects_unknown_prompt_key() -> None:
    registry = PromptRegistry()

    try:
        registry.load("agent.missing")
    except KeyError as exc:
        assert "agent.missing" in str(exc)
    else:
        raise AssertionError("unknown prompt key should raise KeyError")
