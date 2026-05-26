import logging
from types import SimpleNamespace

from service.cart_service import CartService

logger = logging.getLogger(__name__)


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
    - Single: ``dish_id=123, quantity=1``  *(deprecated — use items)*
    - Batch:  ``items=[{"dish_id": 123, "quantity": 1}, ...]``

    When *items* is provided, *dish_id* / *quantity* are ignored.

    **Atomicity:** If any item in a batch fails, all previously-added
    items are rolled back (removed) so the cart is not left dirty.
    """
    service = _cart_service or CartService(session)

    if items:
        # Validate item structure before any processing
        seen_dish_ids: set[int] = set()
        for idx, item in enumerate(items):
            if not isinstance(item, dict) or "dish_id" not in item:
                return {
                    "success": False,
                    "message": f"items[{idx}] 格式错误：每项须为含 dish_id 的字典",
                }
            try:
                did = int(item["dish_id"])
            except (TypeError, ValueError):
                return {
                    "success": False,
                    "message": f"items[{idx}] 的 dish_id 无法解析为整数",
                }
            try:
                qty = int(item.get("quantity", 1))
            except (TypeError, ValueError):
                return {
                    "success": False,
                    "message": f"items[{idx}] 的 quantity 无法解析为整数",
                }
            if qty < 1:
                return {
                    "success": False,
                    "message": f"items[{idx}] 的 quantity 必须 >= 1，当前值为 {qty}",
                }
            # Reject duplicate dish_ids — ambiguous rollback/undo semantics
            if did in seen_dish_ids:
                return {
                    "success": False,
                    "message": f"items 中 dish_id={did} 重复，请合并数量后重试",
                }
            seen_dish_ids.add(did)

        results = []
        # Track pre-add quantities so rollback restores, not deletes.
        rollback_info: list[dict] = []
        for item in items:
            try:
                added_qty = int(item.get("quantity", 1))
                payload = SimpleNamespace(
                    dish_id=int(item["dish_id"]),
                    quantity=added_qty,
                )
                result = service.add_item(user_id, payload)
                post_qty = result.get("quantity", added_qty)
                pre_qty = max(post_qty - added_qty, 0)
                rollback_info.append({
                    "dish_id": int(item["dish_id"]),
                    "added_qty": added_qty,
                    "pre_quantity": pre_qty,
                })
                results.append(result)
            except Exception as exc:
                # Rollback: restore previous quantities, not delete rows
                rolled_back = []
                rollback_failed = []
                for info in rollback_info:
                    try:
                        if info["pre_quantity"] > 0:
                            service.update_item(user_id, info["dish_id"], info["pre_quantity"])
                        else:
                            service.remove_item(user_id, info["dish_id"])
                        rolled_back.append(info["dish_id"])
                    except Exception:
                        logger.warning("add_to_cart rollback: failed to restore dish_id=%d", info["dish_id"])
                        rollback_failed.append(info["dish_id"])
                result_dict: dict = {
                    "success": False,
                    "message": f"添加菜品失败(dish_id={item.get('dish_id')}): {exc}",
                    "failed_dish_id": item.get("dish_id"),
                    "rolled_back": rolled_back,
                }
                if rollback_failed:
                    result_dict["rollback_failed"] = rollback_failed
                return result_dict
        return {
            "success": True,
            "items": results,
            "before_quantities": {info["dish_id"]: info["pre_quantity"] for info in rollback_info},
        }

    # --- Deprecated single-item mode ---
    if dish_id is None:
        return {"success": False, "message": "缺少 dish_id 或 items 参数"}
    logger.warning("add_to_cart called with deprecated dish_id mode (dish_id=%d). Use items=[] instead.", dish_id)
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
