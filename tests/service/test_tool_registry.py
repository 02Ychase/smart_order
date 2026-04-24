from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.tool_registry import ToolRegistry, ToolSchema


def test_registry_registers_and_lists_tools() -> None:
    registry = ToolRegistry()
    schema = ToolSchema(
        name="test_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {"x": {"type": "integer"}}},
    )
    registry.register(schema, lambda **kwargs: {"result": kwargs["x"] * 2})

    schemas = registry.list_schemas()
    assert len(schemas) == 1
    assert schemas[0].name == "test_tool"


def test_registry_executes_tool_by_name() -> None:
    registry = ToolRegistry()
    schema = ToolSchema(
        name="double",
        description="Doubles a number",
        parameters={"type": "object", "properties": {"x": {"type": "integer"}}},
    )
    registry.register(schema, lambda **kwargs: {"result": kwargs["x"] * 2})

    result = registry.execute("double", {"x": 21})
    assert result == {"result": 42}


def test_registry_raises_on_unknown_tool() -> None:
    registry = ToolRegistry()
    try:
        registry.execute("missing", {})
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "missing" in str(e)


def test_registry_schema_tracks_side_effect_and_confirmation_policy() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSchema(
            name="prepare_cart_action",
            description="Prepare cart action",
            parameters={"type": "object"},
            side_effect="pending_write",
            requires_confirmation=True,
        ),
        lambda **kwargs: {"ok": True},
    )

    schema = registry.list_schemas()[0]

    assert schema.side_effect == "pending_write"
    assert schema.requires_confirmation is True


def test_add_to_cart_tool_executes() -> None:
    from service.tools.cart_tool import add_to_cart_tool

    mock_session = MagicMock()
    mock_cart_service = MagicMock()
    mock_cart_service.add_item.return_value = {"success": True, "dish_id": 11, "quantity": 2}

    result = add_to_cart_tool(user_id=1, dish_id=11, quantity=2, session=mock_session, _cart_service=mock_cart_service)

    assert result["success"] is True
    assert result["dish_id"] == 11
    mock_cart_service.add_item.assert_called_once()


def test_save_address_tool_executes() -> None:
    from service.tools.address_tool import save_address_tool

    mock_session = MagicMock()
    mock_profile_service = MagicMock()
    mock_profile_service.create_address.return_value = {"id": 5, "label": "家"}

    result = save_address_tool(
        user_id=1,
        label="家",
        contact_name="张三",
        contact_phone="13800138000",
        city="武汉",
        district="洪山区",
        detail_address="珞喻路123号",
        longitude=114.3,
        latitude=30.5,
        session=mock_session,
        _profile_service=mock_profile_service,
    )

    assert result["id"] == 5
    mock_profile_service.create_address.assert_called_once()
