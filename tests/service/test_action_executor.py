from unittest.mock import MagicMock, patch

from service.agent_runtime.nodes import LocalActionExecutor
from service.agent_runtime.state import AgentPlan, GraphToolCall


class FakeSession:
    """Minimal fake to satisfy LocalActionExecutor(session=...)."""
    def scalars(self, *a, **kw):
        return []


def _mock_journal():
    """Return a mock ActionJournalService that returns a fake record."""
    mock_service = MagicMock()
    mock_service.record_completed_action.return_value = {"action_id": "act_test123"}
    return mock_service


def test_execute_add_to_cart():
    executor = LocalActionExecutor(session=FakeSession())

    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[GraphToolCall(
            tool_name="add_to_cart",
            arguments={"dish_id": 11, "quantity": 2},
            writes_database=True,
        )],
    )
    state = {"user_id": 1, "session_id": "s1", "recent_action_ids": []}

    with patch("service.tools.cart_tool.add_to_cart_tool", return_value={"dish_id": 11, "quantity": 2}), \
         patch("service.action_journal_service.ActionJournalService", return_value=_mock_journal()):
        result = executor.execute_action(plan, state)

    assert result["success"] is True
    assert "action_id" in result


def test_execute_remove_from_cart():
    executor = LocalActionExecutor(session=FakeSession())

    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[GraphToolCall(
            tool_name="remove_from_cart",
            arguments={"dish_id": 11},
            writes_database=True,
        )],
    )
    state = {"user_id": 1, "session_id": "s1", "recent_action_ids": []}

    with patch("service.cart_service.CartService") as MockCart:
        mock_service = MockCart.return_value
        mock_service.remove_item.return_value = None
        result = executor.execute_action(plan, state)

    assert result["success"] is True
    assert result["message"] == "已从购物车移除"


def test_execute_save_address():
    executor = LocalActionExecutor(session=FakeSession())

    plan = AgentPlan(
        intent="address_action",
        tool_calls=[GraphToolCall(
            tool_name="save_address",
            arguments={"label": "家", "contact_name": "张三", "contact_phone": "13800001111",
                        "city": "上海市", "district": "静安区", "detail_address": "南京西路100号",
                        "longitude": 121.45, "latitude": 31.22},
            writes_database=True,
        )],
    )
    state = {"user_id": 1, "session_id": "s1", "recent_action_ids": []}

    with patch("service.tools.address_tool.commit_address_action_tool", return_value={"success": True}), \
         patch("service.action_journal_service.ActionJournalService", return_value=_mock_journal()):
        result = executor.execute_action(plan, state)

    assert result["success"] is True
    assert result["message"] == "已保存配送地址"


def test_execute_upsert_preference():
    executor = LocalActionExecutor(session=FakeSession())

    plan = AgentPlan(
        intent="preference_action",
        tool_calls=[GraphToolCall(
            tool_name="upsert_preference",
            arguments={"memory_type": "food_preference", "content": "不吃花生"},
            writes_database=True,
        )],
    )
    state = {"user_id": 1, "session_id": "s1", "recent_action_ids": []}

    with patch("service.tools.preference_tool.upsert_preference_tool", return_value={
        "success": True,
        "undo_policy": "snapshot_restore",
        "before_snapshot": [],
        "after_snapshot": [],
        "undo_tool": "restore_user_memory_snapshot",
    }), patch("service.action_journal_service.ActionJournalService", return_value=_mock_journal()):
        result = executor.execute_action(plan, state)

    assert result["success"] is True
    assert result["message"] == "已更新用户偏好"
