from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.models.cart import CartItem
from api.models.order import CheckoutOrder, DeliveryQuote, MerchantOrder, OrderItem, PaymentRecord
from api.models.user import UserAddress


class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_address(self, user_id: int, address_id: int) -> UserAddress | None:
        statement = select(UserAddress).where(
            UserAddress.user_id == user_id,
            UserAddress.id == address_id,
        )
        return self.session.scalar(statement)

    def list_cart_items(self, user_id: int) -> list[CartItem]:
        statement = (
            select(CartItem)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.merchant_id.asc(), CartItem.id.asc())
        )
        return list(self.session.scalars(statement))

    def create_checkout_order(self, user_id: int, address_snapshot: str, merchant_orders: list[dict]) -> CheckoutOrder:
        goods_amount = sum((merchant_order["goods_amount"] for merchant_order in merchant_orders), start=0)
        delivery_amount = sum((merchant_order["delivery_amount"] for merchant_order in merchant_orders), start=0)
        payable_amount = goods_amount + delivery_amount

        checkout_order = CheckoutOrder(
            user_id=user_id,
            address_snapshot=address_snapshot,
            goods_amount=goods_amount,
            delivery_amount=delivery_amount,
            payable_amount=payable_amount,
        )
        self.session.add(checkout_order)
        self.session.flush()

        for merchant_order_payload in merchant_orders:
            merchant_order = MerchantOrder(
                checkout_order_id=checkout_order.id,
                merchant_id=merchant_order_payload["merchant_id"],
                goods_amount=merchant_order_payload["goods_amount"],
                delivery_amount=merchant_order_payload["delivery_amount"],
                payable_amount=merchant_order_payload["payable_amount"],
            )
            self.session.add(merchant_order)
            self.session.flush()

            delivery_quote = merchant_order_payload["delivery_quote"]
            self.session.add(
                DeliveryQuote(
                    checkout_order_id=checkout_order.id,
                    merchant_id=merchant_order_payload["merchant_id"],
                    in_range=delivery_quote["in_range"],
                    distance_meters=delivery_quote["distance_meters"],
                    estimated_minutes=delivery_quote["estimated_minutes"],
                    delivery_fee=merchant_order_payload["delivery_amount"],
                    message=delivery_quote["message"],
                )
            )

            for item_payload in merchant_order_payload["items"]:
                self.session.add(
                    OrderItem(
                        merchant_order_id=merchant_order.id,
                        dish_id=item_payload["dish_id"],
                        dish_name_snapshot=item_payload["dish_name"],
                        quantity=item_payload["quantity"],
                        unit_price_snapshot=item_payload["unit_price"],
                    )
                )

        self.session.execute(delete(CartItem).where(CartItem.user_id == user_id))
        self.session.commit()
        self.session.refresh(checkout_order)
        return checkout_order

    def list_checkout_orders(self, user_id: int) -> list[CheckoutOrder]:
        statement = (
            select(CheckoutOrder)
            .where(CheckoutOrder.user_id == user_id)
            .order_by(CheckoutOrder.id.desc())
        )
        return list(self.session.scalars(statement))

    def get_checkout_order(self, checkout_order_id: int) -> CheckoutOrder | None:
        return self.session.get(CheckoutOrder, checkout_order_id)

    def get_checkout_order_for_user(self, user_id: int, checkout_order_id: int) -> CheckoutOrder | None:
        statement = select(CheckoutOrder).where(
            CheckoutOrder.user_id == user_id,
            CheckoutOrder.id == checkout_order_id,
        )
        return self.session.scalar(statement)

    def list_merchant_orders(self, checkout_order_id: int) -> list[MerchantOrder]:
        statement = (
            select(MerchantOrder)
            .where(MerchantOrder.checkout_order_id == checkout_order_id)
            .order_by(MerchantOrder.id.asc())
        )
        return list(self.session.scalars(statement))

    def list_order_items(self, merchant_order_id: int) -> list[OrderItem]:
        statement = (
            select(OrderItem)
            .where(OrderItem.merchant_order_id == merchant_order_id)
            .order_by(OrderItem.id.asc())
        )
        return list(self.session.scalars(statement))

    def list_delivery_quotes(self, checkout_order_id: int) -> list[DeliveryQuote]:
        statement = (
            select(DeliveryQuote)
            .where(DeliveryQuote.checkout_order_id == checkout_order_id)
            .order_by(DeliveryQuote.merchant_id.asc(), DeliveryQuote.id.asc())
        )
        return list(self.session.scalars(statement))

    def get_payment_record(self, checkout_order_id: int) -> PaymentRecord | None:
        statement = select(PaymentRecord).where(PaymentRecord.checkout_order_id == checkout_order_id)
        return self.session.scalar(statement)

    def mark_paid(self, user_id: int, checkout_order_id: int, request_no: str) -> CheckoutOrder | None:
        checkout_order = self.get_checkout_order_for_user(user_id, checkout_order_id)
        if checkout_order is None:
            return None

        checkout_order.payment_status = "paid"
        checkout_order.order_status = "paid"

        for merchant_order in self.list_merchant_orders(checkout_order_id):
            merchant_order.order_status = "paid"

        payment_record = self.get_payment_record(checkout_order_id)
        if payment_record is None:
            self.session.add(
                PaymentRecord(
                    checkout_order_id=checkout_order_id,
                    request_no=request_no,
                    payment_status="succeeded",
                )
            )

        self.session.commit()
        self.session.refresh(checkout_order)
        return checkout_order
