from service.tools.address_tool import build_address_payload, commit_address_action_tool
from service.tools.cart_tool import commit_cart_action_tool


class StubCartService:
    def __init__(self):
        self.added = []

    def add_item(self, user_id, payload):
        self.added.append((user_id, payload.dish_id, payload.quantity))
        return {"success": True, "dish_id": payload.dish_id, "quantity": payload.quantity}


class StubProfileService:
    def create_address(self, user_id, payload):
        return {"id": 7, "label": payload.label, "contact_phone": payload.contact_phone}


def test_commit_cart_action_adds_each_item() -> None:
    service = StubCartService()

    result = commit_cart_action_tool(
        user_id=1,
        items=[{"dish_id": 11, "quantity": 1}, {"dish_id": 12, "quantity": 2}],
        _cart_service=service,
    )

    assert result["success"] is True
    assert service.added == [(1, 11, 1), (1, 12, 2)]


def test_build_address_payload_has_model_dump() -> None:
    payload = build_address_payload(
        label="家",
        contact_name="张三",
        contact_phone="13800000000",
        city="上海市",
        district="静安区",
        detail_address="南京西路818号",
        longitude=121.45,
        latitude=31.22,
        is_default=False,
    )

    assert payload.model_dump()["contact_name"] == "张三"


def test_commit_address_action_uses_profile_service() -> None:
    result = commit_address_action_tool(
        user_id=1,
        address={
            "label": "家",
            "contact_name": "张三",
            "contact_phone": "13800000000",
            "city": "上海市",
            "district": "静安区",
            "detail_address": "南京西路818号",
            "longitude": 121.45,
            "latitude": 31.22,
            "is_default": False,
        },
        _profile_service=StubProfileService(),
    )

    assert result["id"] == 7
    assert result["contact_phone"] == "13800000000"
