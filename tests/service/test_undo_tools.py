from service.tools.cart_tool import clear_cart_tool, restore_cart_snapshot_tool
from service.tools.preference_tool import upsert_preference_tool


class StubCartService:
    def __init__(self):
        self.cart = {
            "items": [
                {
                    "merchant_id": 1,
                    "merchant_name": "兰姨小炒",
                    "items": [
                        {
                            "dish_id": 11,
                            "dish_name": "小炒黄牛肉",
                            "quantity": 2,
                            "unit_price": 42.0,
                        }
                    ],
                    "subtotal": 84.0,
                }
            ],
            "goods_amount": 84.0,
        }
        self.added = []
        self.removed = []

    def get_grouped_cart(self, user_id):
        return self.cart

    def remove_item(self, user_id, dish_id):
        self.removed.append(dish_id)
        self.cart = {"items": [], "goods_amount": 0}
        return {"success": True, "dish_id": dish_id}

    def add_item(self, user_id, payload):
        self.added.append({"dish_id": payload.dish_id, "quantity": payload.quantity})
        return {
            "success": True,
            "dish_id": payload.dish_id,
            "quantity": payload.quantity,
        }


def test_clear_cart_tool_returns_before_and_after_snapshots() -> None:
    service = StubCartService()

    result = clear_cart_tool(user_id=9, _cart_service=service)

    assert result["success"] is True
    assert result["before_snapshot"]["items"][0]["items"][0]["dish_id"] == 11
    assert result["after_snapshot"]["items"] == []


def test_restore_cart_snapshot_readds_previous_items() -> None:
    service = StubCartService()
    snapshot = {"items": [{"merchant_id": 1, "items": [{"dish_id": 11, "quantity": 2}]}]}

    result = restore_cart_snapshot_tool(user_id=9, snapshot=snapshot, _cart_service=service)

    assert result["success"] is True
    assert service.added == [{"dish_id": 11, "quantity": 2}]


class StubMemoryService:
    def __init__(self):
        self.memories = [{"memory_type": "taste", "content": "少油"}]

    def list_memories(self, user_id):
        return list(self.memories)

    def upsert_memory(self, user_id, memory_type, content, confidence):
        memory = {
            "user_id": user_id,
            "memory_type": memory_type,
            "content": content,
            "confidence": confidence,
        }
        self.memories.append(memory)
        return memory


def test_upsert_preference_tool_returns_snapshots_for_undo() -> None:
    service = StubMemoryService()

    result = upsert_preference_tool(
        user_id=9,
        memory_type="taste",
        content="喜欢辣的湘菜",
        _memory_service=service,
    )

    assert result["success"] is True
    assert result["before_snapshot"] == [{"memory_type": "taste", "content": "少油"}]
    assert result["after_snapshot"][-1]["content"] == "喜欢辣的湘菜"
    assert result["undo_tool"] == "restore_user_memory_snapshot"
