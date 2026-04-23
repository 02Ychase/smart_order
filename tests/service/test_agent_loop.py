from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.agent_loop import AgentLoop


def test_agent_loop_runs_tool_for_direct_action() -> None:
    loop = AgentLoop(session=MagicMock())

    tool_result = {"success": True, "dish_id": 11, "quantity": 1}
    loop.tool_registry.execute = MagicMock(return_value=tool_result)

    with patch("service.agent_loop.call_llm", return_value='{"thought": "用户想加购", "action": "add_to_cart", "action_input": {"user_id": 1, "dish_id": 11, "quantity": 1}}'):
        result = loop.run(
            intent="action_intent",
            user_message="帮我加入购物车",
            constraints=None,
            user_id=1,
        )

    assert result["response_type"] == "action_completed"
    assert result["tool_result"] == tool_result
    loop.tool_registry.execute.assert_called_once_with("add_to_cart", {"user_id": 1, "dish_id": 11, "quantity": 1})


def test_agent_loop_returns_direct_response_for_greeting() -> None:
    loop = AgentLoop(session=MagicMock())

    result = loop.run(
        intent="greeting",
        user_message="Hi",
        constraints=None,
        user_id=1,
    )

    assert result["response_type"] == "greeting"
    assert "message" in result
