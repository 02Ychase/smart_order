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
