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

    with patch("service.tools.cart_tool.add_to_cart_tool", return_value={"success": True, "items": [{"dish_id": 11, "quantity": 2}]}), \
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


def test_execute_batch_add_to_cart():
    """Batch add_to_cart should add multiple dishes in a single call."""
    executor = LocalActionExecutor(session=FakeSession())

    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[GraphToolCall(
            tool_name="add_to_cart",
            arguments={"items": [
                {"dish_id": 11, "quantity": 1},
                {"dish_id": 22, "quantity": 1},
                {"dish_id": 33, "quantity": 2},
            ]},
            writes_database=True,
        )],
    )
    state = {"user_id": 1, "session_id": "s1", "recent_action_ids": [], "tool_results": []}

    with patch("service.tools.cart_tool.add_to_cart_tool", return_value={
        "success": True,
        "items": [
            {"success": True, "dish_id": 11, "quantity": 1},
            {"success": True, "dish_id": 22, "quantity": 1},
            {"success": True, "dish_id": 33, "quantity": 2},
        ],
    }), patch("service.action_journal_service.ActionJournalService", return_value=_mock_journal()):
        result = executor.execute_action(plan, state)

    assert result["success"] is True
    assert "3 道菜品" in result["message"]
    assert "action_id" in result


def test_execute_add_to_cart_items_batch():
    """Batch add_to_cart with items list should work and report correct count."""
    executor = LocalActionExecutor(session=FakeSession())

    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[GraphToolCall(
            tool_name="add_to_cart",
            arguments={"items": [
                {"dish_id": 11, "quantity": 1},
                {"dish_id": 22, "quantity": 2},
            ]},
            writes_database=True,
        )],
    )
    state = {"user_id": 1, "session_id": "s1", "recent_action_ids": [], "tool_results": []}

    with patch("service.tools.cart_tool.add_to_cart_tool", return_value={
        "success": True,
        "items": [
            {"success": True, "dish_id": 11, "quantity": 1},
            {"success": True, "dish_id": 22, "quantity": 2},
        ],
    }) as mock_tool, patch("service.action_journal_service.ActionJournalService", return_value=_mock_journal()):
        result = executor.execute_action(plan, state)

    assert result["success"] is True
    assert "2 道菜品" in result["message"]
    # Verify called with items= kwarg
    _, call_kwargs = mock_tool.call_args
    assert "items" in call_kwargs


def test_execute_add_to_cart_old_format_normalizes_to_items():
    """Old dish_id+quantity format should be normalized to items=[{...}]."""
    executor = LocalActionExecutor(session=FakeSession())

    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[GraphToolCall(
            tool_name="add_to_cart",
            arguments={"dish_id": 11, "quantity": 2},
            writes_database=True,
        )],
    )
    state = {"user_id": 1, "session_id": "s1", "recent_action_ids": [], "tool_results": []}

    with patch("service.tools.cart_tool.add_to_cart_tool", return_value={
        "success": True,
    }) as mock_tool, patch("service.action_journal_service.ActionJournalService", return_value=_mock_journal()):
        result = executor.execute_action(plan, state)

    assert result["success"] is True
    assert "1 道菜品" in result["message"]
    # Verify normalized: called with items=[{dish_id:11, quantity:2}]
    _, call_kwargs = mock_tool.call_args
    assert "items" in call_kwargs
    assert call_kwargs["items"] == [{"dish_id": 11, "quantity": 2}]


def test_execute_add_to_cart_empty_items_fails():
    """Empty items list should fail, even when evidence exists (no bridging)."""
    executor = LocalActionExecutor(session=FakeSession())

    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[GraphToolCall(
            tool_name="add_to_cart",
            arguments={"items": []},
            writes_database=True,
        )],
    )
    state = {
        "user_id": 1,
        "session_id": "s1",
        "recent_action_ids": [],
        "tool_results": [],
        "recent_evidence": [
            {"source_type": "dish", "facts": {"dish_id": 100}},
        ],
    }

    result = executor.execute_action(plan, state)

    assert result["success"] is False
    assert "items" in result["message"]


def test_execute_add_to_cart_partial_failure():
    """If cart_tool returns success=False, execute_action should not record journal."""
    executor = LocalActionExecutor(session=FakeSession())

    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[GraphToolCall(
            tool_name="add_to_cart",
            arguments={"items": [
                {"dish_id": 11, "quantity": 1},
                {"dish_id": 999, "quantity": 1},
            ]},
            writes_database=True,
        )],
    )
    state = {"user_id": 1, "session_id": "s1", "recent_action_ids": [], "tool_results": []}

    partial_result = {
        "success": False,
        "message": "部分菜品添加失败: 1/2",
        "items": [{"dish_id": 11, "quantity": 1}],
        "failed": [{"dish_id": 999, "error": "Dish not found"}],
    }

    with patch("service.tools.cart_tool.add_to_cart_tool", return_value=partial_result):
        result = executor.execute_action(plan, state)

    assert result["success"] is False
    assert "失败" in result["message"]


def test_execute_add_to_cart_no_dish_id_no_items_fails():
    """Missing both items and dish_id should fail, even when evidence exists."""
    executor = LocalActionExecutor(session=FakeSession())

    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[GraphToolCall(
            tool_name="add_to_cart",
            arguments={},
            writes_database=True,
        )],
    )
    state = {
        "user_id": 1,
        "session_id": "s1",
        "recent_action_ids": [],
        "tool_results": [],
        "recent_evidence": [
            {"source_type": "dish", "facts": {"dish_id": 100}},
            {"source_type": "dish", "facts": {"dish_id": 200}},
        ],
    }

    result = executor.execute_action(plan, state)

    assert result["success"] is False


def test_execute_add_to_cart_summary_includes_dish_names():
    """add_to_cart summary should include dish names and prices from evidence."""
    executor = LocalActionExecutor(session=FakeSession())

    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[GraphToolCall(
            tool_name="add_to_cart",
            arguments={"items": [
                {"dish_id": 12, "quantity": 1},
                {"dish_id": 35, "quantity": 1},
            ]},
            writes_database=True,
            step_id="add_to_cart_0",
        )],
    )
    state = {
        "user_id": 1,
        "session_id": "s1",
        "tool_results": [],
        "recent_evidence": [
            {"source_type": "dish", "source_id": 12, "facts": {"dish_id": 12, "dish_name": "宫保鸡丁", "price": 28.0}},
            {"source_type": "dish", "source_id": 35, "facts": {"dish_id": 35, "dish_name": "水煮鱼", "price": 45.0}},
        ],
    }

    with patch("service.tools.cart_tool.add_to_cart_tool", return_value={"success": True, "items": []}) as mock_tool, \
         patch("service.action_journal_service.ActionJournalService", return_value=_mock_journal()):
        result = executor.execute_action(plan, state)

    assert result["success"] is True
    assert "宫保鸡丁" in result["message"]
    assert "水煮鱼" in result["message"]
    assert "¥28" in result["message"]


def test_execute_add_to_cart_summary_fallback_without_evidence():
    """Without evidence, summary should fall back to dish ID placeholders."""
    executor = LocalActionExecutor(session=FakeSession())

    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[GraphToolCall(
            tool_name="add_to_cart",
            arguments={"items": [{"dish_id": 99, "quantity": 1}]},
            writes_database=True,
        )],
    )
    state = {"user_id": 1, "session_id": "s1", "tool_results": [], "recent_evidence": []}

    with patch("service.tools.cart_tool.add_to_cart_tool", return_value={"success": True, "items": []}), \
         patch("service.action_journal_service.ActionJournalService", return_value=_mock_journal()):
        result = executor.execute_action(plan, state)

    assert result["success"] is True
    assert "菜品99" in result["message"]
