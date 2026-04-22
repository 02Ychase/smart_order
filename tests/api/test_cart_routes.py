import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_DATABASE_PATH = PROJECT_ROOT / "test_cart_routes.db"
TEST_DATABASE_PATH.unlink(missing_ok=True)

os.environ["JWT_SECRET_KEY"] = "test-phase1-secret"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

from api.db import engine
from api.main import app
from api.models.cart import Cart
from api.models.user import User
from api.routes import cart as cart_routes


User.__table__.create(bind=engine, checkfirst=True)
Cart.__table__.create(bind=engine, checkfirst=True)
client = TestClient(app, raise_server_exceptions=False)



def _count_carts() -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(Cart)) or 0



def test_get_cart_returns_grouped_merchants(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routes.cart.CartService.get_grouped_cart",
        lambda self, user_id: {
            "items": [
                {
                    "merchant_id": 1,
                    "merchant_name": "川湘小馆",
                    "items": [{"dish_id": 11, "dish_name": "鱼香肉丝", "quantity": 2, "unit_price": 28.0}],
                    "subtotal": 56.0,
                }
            ],
            "goods_amount": 56.0,
        },
    )
    monkeypatch.setattr(
        "api.routes.cart.CartService.add_item",
        lambda self, user_id, payload: {"success": True, "dish_id": payload.dish_id, "quantity": payload.quantity},
    )
    monkeypatch.setattr(
        "api.routes.cart.CartService.remove_item",
        lambda self, user_id, dish_id: {"success": True, "dish_id": dish_id},
    )

    app.dependency_overrides[cart_routes.get_current_user] = lambda: type("User", (), {"id": 9})()
    try:
        get_response = client.get("/cart")
        assert get_response.status_code == 200
        assert get_response.json()["items"][0]["merchant_name"] == "川湘小馆"

        add_response = client.post("/cart/items", json={"dish_id": 11, "quantity": 2})
        assert add_response.status_code == 200
        assert add_response.json() == {"success": True, "dish_id": 11, "quantity": 2}

        remove_response = client.delete("/cart/items/11")
        assert remove_response.status_code == 200
        assert remove_response.json() == {"success": True, "dish_id": 11}
    finally:
        app.dependency_overrides.clear()



def test_get_cart_without_existing_cart_returns_empty_and_does_not_create_cart() -> None:
    app.dependency_overrides[cart_routes.get_current_user] = lambda: type("User", (), {"id": 9})()
    try:
        assert _count_carts() == 0

        response = client.get("/cart")

        assert response.status_code == 200
        assert response.json() == {"items": [], "goods_amount": 0}
        assert _count_carts() == 0
    finally:
        app.dependency_overrides.clear()



def test_delete_missing_cart_item_does_not_create_cart() -> None:
    app.dependency_overrides[cart_routes.get_current_user] = lambda: type("User", (), {"id": 9})()
    try:
        assert _count_carts() == 0

        response = client.delete("/cart/items/11")

        assert response.status_code == 404
        assert response.json() == {"detail": "cart item not found"}
        assert _count_carts() == 0
    finally:
        app.dependency_overrides.clear()



def test_adding_same_dish_twice_increments_quantity() -> None:
    from api.models.cart import CartItem
    from api.models.catalog import Dish, DishCategory, Merchant
    from sqlalchemy.orm import Session

    Merchant.__table__.create(bind=engine, checkfirst=True)
    DishCategory.__table__.create(bind=engine, checkfirst=True)
    Dish.__table__.create(bind=engine, checkfirst=True)
    CartItem.__table__.create(bind=engine, checkfirst=True)

    with Session(engine) as session:
        user = User(username="cart_user", password_hash="secret", full_name="购物车用户", phone="13900000000")
        session.add(user)
        session.flush()

        merchant = Merchant(
            name="川湘小馆",
            description="下饭家常菜",
            city="上海",
            district="静安",
            address="南京西路 100 号",
            longitude=121.45,
            latitude=31.23,
        )
        session.add(merchant)
        session.flush()

        category = DishCategory(merchant_id=merchant.id, name="招牌菜", sort_order=1)
        session.add(category)
        session.flush()

        dish = Dish(
            merchant_id=merchant.id,
            category_id=category.id,
            name="鱼香肉丝",
            description="酸甜开胃",
            price=28,
        )
        session.add(dish)
        session.commit()
        user_id = user.id
        dish_id = dish.id

    app.dependency_overrides[cart_routes.get_current_user] = lambda: type("User", (), {"id": user_id})()
    try:
        first_response = client.post("/cart/items", json={"dish_id": dish_id, "quantity": 1})
        second_response = client.post("/cart/items", json={"dish_id": dish_id, "quantity": 1})
        cart_response = client.get("/cart")

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        assert second_response.json() == {"success": True, "dish_id": dish_id, "quantity": 2}
        assert cart_response.status_code == 200
        assert cart_response.json()["items"][0]["items"] == [
            {"dish_id": dish_id, "dish_name": "鱼香肉丝", "quantity": 2, "unit_price": 28.0}
        ]
        assert cart_response.json()["goods_amount"] == 56.0
    finally:
        app.dependency_overrides.clear()
