from types import SimpleNamespace

from service.cart_service import CartService


def add_to_cart_tool(
    user_id: int,
    dish_id: int | None = None,
    quantity: int = 1,
    items: list[dict] | None = None,
    session=None,
    _cart_service=None,
) -> dict:
    """Add one or more dishes to the user's shopping cart.

    Supports two modes:
    - Single: ``dish_id=123, quantity=1``
    - Batch:  ``items=[{"dish_id": 123, "quantity": 1}, ...]``

    When *items* is provided, *dish_id* / *quantity* are ignored.
    """
    service = _cart_service or CartService(session)

    if items:
        results = []
        failed = []
        for item in items:
            try:
                payload = SimpleNamespace(
                    dish_id=int(item["dish_id"]),
                    quantity=int(item.get("quantity", 1)),
                )
                result = service.add_item(user_id, payload)
                results.append(result)
            except Exception as exc:
                failed.append({"dish_id": item.get("dish_id"), "error": str(exc)})
        if failed:
            return {
                "success": False,
                "message": f"部分菜品添加失败: {len(failed)}/{len(items)}",
                "items": results,
                "failed": failed,
            }
        return {"success": True, "items": results}

    if dish_id is None:
        return {"success": False, "message": "缺少 dish_id 或 items 参数"}
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
