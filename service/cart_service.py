from collections import OrderedDict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repository.cart_repository import CartRepository


class CartService:
    def __init__(self, session: Session):
        self.carts = CartRepository(session)

    def get_grouped_cart(self, user_id: int) -> dict:
        grouped = OrderedDict()
        for item in self.carts.list_items(user_id):
            merchant = self.carts.get_merchant(item.merchant_id)
            bucket = grouped.setdefault(
                item.merchant_id,
                {
                    "merchant_id": item.merchant_id,
                    "merchant_name": merchant.name if merchant else f"merchant-{item.merchant_id}",
                    "items": [],
                    "subtotal": 0.0,
                },
            )
            dish = self.carts.get_dish(item.dish_id)
            row_total = float(item.unit_price_snapshot) * item.quantity
            bucket["items"].append(
                {
                    "dish_id": item.dish_id,
                    "dish_name": dish.name if dish else f"dish-{item.dish_id}",
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price_snapshot),
                }
            )
            bucket["subtotal"] += row_total

        goods_amount = sum(group["subtotal"] for group in grouped.values())
        return {"items": list(grouped.values()), "goods_amount": goods_amount}

    def add_item(self, user_id: int, payload) -> dict:
        try:
            item = self.carts.upsert_item(user_id, payload.dish_id, payload.quantity)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dish not found") from exc
        return {"success": True, "dish_id": item.dish_id, "quantity": item.quantity}

    def update_item(self, user_id: int, dish_id: int, quantity: int) -> dict:
        if quantity <= 0:
            deleted = self.carts.remove_item(user_id, dish_id)
            if not deleted:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cart item not found")
            return {"success": True, "dish_id": dish_id, "quantity": 0}
        updated = self.carts.set_item_quantity(user_id, dish_id, quantity)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cart item not found")
        return {"success": True, "dish_id": dish_id, "quantity": quantity}

    def remove_item(self, user_id: int, dish_id: int) -> dict:
        deleted = self.carts.remove_item(user_id, dish_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cart item not found")
        return {"success": True, "dish_id": dish_id}
