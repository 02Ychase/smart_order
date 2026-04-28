from types import SimpleNamespace

from service.cart_service import CartService


def add_to_cart_tool(
    user_id: int,
    dish_id: int,
    quantity: int = 1,
    session=None,
    _cart_service=None,
) -> dict:
    """Add a dish to the user's shopping cart.

    Args:
        user_id: The user's ID
        dish_id: The dish ID to add
        quantity: Number of portions (default 1)
        session: SQLAlchemy session (injected by caller)
        _cart_service: Optional mock for testing
    """
    service = _cart_service or CartService(session)
    payload = SimpleNamespace(dish_id=dish_id, quantity=quantity)
    return service.add_item(user_id, payload)


def commit_cart_action_tool(
    user_id: int,
    items: list[dict],
    session=None,
    _cart_service=None,
) -> dict:
    service = _cart_service or CartService(session)
    results = []
    for item in items:
        payload = SimpleNamespace(
            dish_id=int(item["dish_id"]),
            quantity=int(item.get("quantity", 1)),
        )
        results.append(service.add_item(user_id, payload))
    return {"success": True, "items": results}


def clear_cart_tool(user_id: int, session=None, _cart_service=None) -> dict:
    service = _cart_service or CartService(session)
    before_snapshot = service.get_grouped_cart(user_id)
    for group in before_snapshot.get("items", []):
        for item in group.get("items", []):
            service.remove_item(user_id, int(item["dish_id"]))
    after_snapshot = service.get_grouped_cart(user_id)
    return {
        "success": True,
        "before_snapshot": before_snapshot,
        "after_snapshot": after_snapshot,
        "undo_policy": "snapshot_restore",
        "undo_tool": "restore_cart_snapshot",
        "natural_summary": "清空购物车",
    }


def restore_cart_snapshot_tool(
    user_id: int,
    snapshot: dict,
    session=None,
    _cart_service=None,
) -> dict:
    service = _cart_service or CartService(session)
    restored = []
    for group in snapshot.get("items", []):
        for item in group.get("items", []):
            payload = SimpleNamespace(
                dish_id=int(item["dish_id"]),
                quantity=int(item.get("quantity", 1)),
            )
            restored.append(service.add_item(user_id, payload))
    return {"success": True, "restored": restored}
