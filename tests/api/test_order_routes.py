import os
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_DATABASE_PATH = PROJECT_ROOT / "test_order_routes.db"
TEST_DATABASE_PATH.unlink(missing_ok=True)

os.environ["JWT_SECRET_KEY"] = "test-phase1-secret"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

from api.db import engine
from api.main import app
from api.models import Base
from api.models.cart import Cart, CartItem
from api.models.catalog import Dish, DishCategory, Merchant
from api.models.user import User, UserAddress
from api.routes import orders as orders_routes


Base.metadata.create_all(bind=engine)
client = TestClient(app, raise_server_exceptions=False)



def test_orders_register_as_single_route_for_get_and_post() -> None:
    order_routes = [route for route in app.routes if route.path == "/orders"]

    assert len(order_routes) == 1
    assert {"GET", "POST"}.issubset(order_routes[0].methods)



def test_orders_openapi_keeps_distinct_get_and_post_metadata() -> None:
    operations = app.openapi()["paths"]["/orders"]

    assert operations["get"]["operationId"] != operations["post"]["operationId"]
    assert "requestBody" not in operations["get"]
    assert operations["get"]["responses"]["200"]["content"]["application/json"]["schema"]["type"] == "array"
    assert "items" in operations["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert "201" in operations["post"]["responses"]
    assert "$ref" in operations["post"]["responses"]["201"]["content"]["application/json"]["schema"]



def _seed_checkout_fixture() -> dict:
    suffix = uuid4().hex[:8]
    with Session(engine) as session:
        user = User(
            username=f"order-user-{suffix}",
            password_hash="hashed-password",
            full_name="Order User",
            phone=f"138{suffix[:8]}",
        )
        session.add(user)
        session.flush()

        address = UserAddress(
            user_id=user.id,
            label="home",
            contact_name="Order User",
            contact_phone="13800000000",
            city="上海市",
            district="浦东新区",
            detail_address="世纪大道100号",
            longitude=121.5000,
            latitude=31.2350,
            is_default=True,
        )
        session.add(address)
        session.flush()

        merchant_a = Merchant(
            name="川湘小馆",
            description="热辣下饭",
            city="上海市",
            district="浦东新区",
            address="张杨路1号",
            longitude=121.5010,
            latitude=31.2355,
            delivery_radius_meters=3000,
            delivery_fee=Decimal("4.00"),
            min_order_amount=Decimal("20.00"),
            avg_delivery_minutes=28,
            rating=Decimal("4.60"),
            is_open=True,
        )
        merchant_b = Merchant(
            name="轻食能量站",
            description="健康轻食",
            city="上海市",
            district="浦东新区",
            address="商城路8号",
            longitude=121.5030,
            latitude=31.2360,
            delivery_radius_meters=3000,
            delivery_fee=Decimal("6.00"),
            min_order_amount=Decimal("15.00"),
            avg_delivery_minutes=32,
            rating=Decimal("4.80"),
            is_open=True,
        )
        session.add_all([merchant_a, merchant_b])
        session.flush()

        category_a = DishCategory(merchant_id=merchant_a.id, name="招牌", sort_order=1)
        category_b = DishCategory(merchant_id=merchant_b.id, name="轻食", sort_order=1)
        session.add_all([category_a, category_b])
        session.flush()

        dish_a = Dish(
            merchant_id=merchant_a.id,
            category_id=category_a.id,
            name="鱼香肉丝",
            description="下饭招牌",
            price=Decimal("28.00"),
            image_url="",
            tags="招牌,热卖",
            is_recommended=True,
            is_available=True,
        )
        dish_b = Dish(
            merchant_id=merchant_b.id,
            category_id=category_b.id,
            name="鸡胸沙拉",
            description="高蛋白低负担",
            price=Decimal("22.00"),
            image_url="",
            tags="轻食",
            is_recommended=True,
            is_available=True,
        )
        session.add_all([dish_a, dish_b])
        session.flush()

        cart = Cart(user_id=user.id)
        session.add(cart)
        session.flush()

        session.add_all(
            [
                CartItem(
                    cart_id=cart.id,
                    user_id=user.id,
                    merchant_id=merchant_a.id,
                    dish_id=dish_a.id,
                    quantity=2,
                    unit_price_snapshot=Decimal("28.00"),
                ),
                CartItem(
                    cart_id=cart.id,
                    user_id=user.id,
                    merchant_id=merchant_b.id,
                    dish_id=dish_b.id,
                    quantity=1,
                    unit_price_snapshot=Decimal("22.00"),
                ),
            ]
        )
        session.commit()
        return {"user_id": user.id, "address_id": address.id}



def test_order_routes_cover_preview_submit_mock_pay_list_and_detail() -> None:
    fixture = _seed_checkout_fixture()
    app.dependency_overrides[orders_routes.get_current_user] = lambda: type("User", (), {"id": fixture["user_id"]})()
    try:
        preview_response = client.post("/orders/preview", json={"address_id": fixture["address_id"]})
        assert preview_response.status_code == 200
        preview_payload = preview_response.json()
        assert preview_payload["goods_amount"] == 78.0
        assert preview_payload["delivery_amount"] == 10.0
        assert preview_payload["payable_amount"] == 88.0
        assert len(preview_payload["merchant_orders"]) == 2
        assert preview_payload["merchant_orders"][0]["merchant_name"] == "川湘小馆"
        assert preview_payload["merchant_orders"][0]["delivery_quote"]["in_range"] is True

        submit_response = client.post("/orders", json={"address_id": fixture["address_id"]})
        assert submit_response.status_code == 201
        submit_payload = submit_response.json()
        assert submit_payload["payment_status"] == "pending_payment"
        assert submit_payload["order_status"] == "pending_payment"
        assert len(submit_payload["merchant_orders"]) == 2
        assert submit_payload["merchant_orders"][0]["items"][0]["dish_name"] == "鱼香肉丝"

        checkout_order_id = submit_payload["checkout_order_id"]

        mock_pay_response = client.post("/orders/mock-pay", json={"checkout_order_id": checkout_order_id})
        assert mock_pay_response.status_code == 200
        assert mock_pay_response.json() == {
            "success": True,
            "checkout_order_id": checkout_order_id,
            "payment_status": "paid",
            "order_status": "paid",
        }

        list_response = client.get("/orders")
        assert list_response.status_code == 200
        list_payload = list_response.json()
        assert len(list_payload) == 1
        assert list_payload[0]["checkout_order_id"] == checkout_order_id
        assert list_payload[0]["payment_status"] == "paid"
        assert "items" not in list_payload[0]["merchant_orders"][0]

        detail_response = client.get(f"/orders/{checkout_order_id}")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert detail_payload["checkout_order_id"] == checkout_order_id
        assert detail_payload["payment_status"] == "paid"
        assert detail_payload["merchant_orders"][1]["items"][0]["dish_name"] == "鸡胸沙拉"
        assert detail_payload["merchant_orders"][1]["delivery_quote"]["delivery_fee"] == 6.0
    finally:
        app.dependency_overrides.clear()



def test_mock_pay_rejects_order_owned_by_another_user() -> None:
    fixture = _seed_checkout_fixture()
    app.dependency_overrides[orders_routes.get_current_user] = lambda: type("User", (), {"id": fixture["user_id"]})()
    try:
        submit_response = client.post("/orders", json={"address_id": fixture["address_id"]})
        assert submit_response.status_code == 201
        checkout_order_id = submit_response.json()["checkout_order_id"]

        with Session(engine) as session:
            other_suffix = uuid4().hex[:8]
            other_user = User(
                username=f"other-order-user-{other_suffix}",
                password_hash="hashed-password",
                full_name="Other User",
                phone=f"139{other_suffix[:8]}",
            )
            session.add(other_user)
            session.commit()
            other_user_id = other_user.id

        app.dependency_overrides[orders_routes.get_current_user] = lambda: type("User", (), {"id": other_user_id})()

        mock_pay_response = client.post("/orders/mock-pay", json={"checkout_order_id": checkout_order_id})
        assert mock_pay_response.status_code == 404
        assert mock_pay_response.json() == {"detail": "order not found"}
    finally:
        app.dependency_overrides.clear()
