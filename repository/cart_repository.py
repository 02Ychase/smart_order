from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.cart import Cart, CartItem
from api.models.catalog import Dish, Merchant


class CartRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_cart(self, user_id: int) -> Cart | None:
        return self.session.scalar(select(Cart).where(Cart.user_id == user_id))

    def get_or_create_cart(self, user_id: int) -> Cart:
        cart = self.get_cart(user_id)
        if cart is None:
            cart = Cart(user_id=user_id)
            self.session.add(cart)
            self.session.commit()
            self.session.refresh(cart)
        return cart

    def list_items(self, user_id: int) -> list[CartItem]:
        cart = self.get_cart(user_id)
        if cart is None:
            return []

        statement = (
            select(CartItem)
            .where(CartItem.cart_id == cart.id)
            .order_by(CartItem.merchant_id.asc(), CartItem.id.asc())
        )
        return list(self.session.scalars(statement))

    def get_dish(self, dish_id: int) -> Dish | None:
        return self.session.get(Dish, dish_id)

    def get_merchant(self, merchant_id: int) -> Merchant | None:
        return self.session.get(Merchant, merchant_id)

    def upsert_item(self, user_id: int, dish_id: int, quantity: int) -> CartItem:
        cart = self.get_or_create_cart(user_id)
        statement = select(CartItem).where(CartItem.cart_id == cart.id, CartItem.dish_id == dish_id)
        item = self.session.scalar(statement)
        dish = self.get_dish(dish_id)
        if dish is None:
            raise ValueError("dish not found")

        if item is None:
            item = CartItem(
                cart_id=cart.id,
                user_id=user_id,
                merchant_id=dish.merchant_id,
                dish_id=dish.id,
                quantity=quantity,
                unit_price_snapshot=dish.price,
            )
            self.session.add(item)
        else:
            item.quantity += quantity
            item.unit_price_snapshot = dish.price

        self.session.commit()
        self.session.refresh(item)
        return item

    def remove_item(self, user_id: int, dish_id: int) -> bool:
        cart = self.get_cart(user_id)
        if cart is None:
            return False

        statement = select(CartItem).where(CartItem.cart_id == cart.id, CartItem.dish_id == dish_id)
        item = self.session.scalar(statement)
        if item is None:
            return False

        self.session.delete(item)
        self.session.commit()
        return True
