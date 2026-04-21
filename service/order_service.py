from collections import OrderedDict
from decimal import Decimal
from math import cos, radians, sqrt
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repository.cart_repository import CartRepository
from repository.order_repository import OrderRepository


class OrderService:
    def __init__(self, session: Session):
        self.orders = OrderRepository(session)
        self.carts = CartRepository(session)

    def _serialize_address_snapshot(self, address) -> str:
        return (
            f"{address.label} | {address.contact_name} {address.contact_phone} | "
            f"{address.city}{address.district}{address.detail_address}"
        )

    def _distance_meters(self, longitude1: float, latitude1: float, longitude2: float, latitude2: float) -> int:
        latitude_distance = (latitude1 - latitude2) * 111_000
        mean_latitude = radians((latitude1 + latitude2) / 2)
        longitude_distance = (longitude1 - longitude2) * 111_000 * cos(mean_latitude)
        return int(sqrt(latitude_distance**2 + longitude_distance**2))

    def _build_checkout_payload(self, user_id: int, address_id: int) -> dict:
        address = self.orders.get_address(user_id, address_id)
        if address is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="address not found")

        cart_items = self.orders.list_cart_items(user_id)
        if not cart_items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cart is empty")

        grouped: OrderedDict[int, dict] = OrderedDict()
        for cart_item in cart_items:
            merchant = self.carts.get_merchant(cart_item.merchant_id)
            if merchant is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="merchant not found")

            dish = self.carts.get_dish(cart_item.dish_id)
            dish_name = dish.name if dish else f"dish-{cart_item.dish_id}"

            bucket = grouped.setdefault(
                cart_item.merchant_id,
                {
                    "merchant_id": merchant.id,
                    "merchant_name": merchant.name,
                    "merchant_min_order_amount": merchant.min_order_amount,
                    "merchant_delivery_radius_meters": merchant.delivery_radius_meters,
                    "merchant_delivery_fee": merchant.delivery_fee,
                    "merchant_avg_delivery_minutes": merchant.avg_delivery_minutes,
                    "merchant_longitude": merchant.longitude,
                    "merchant_latitude": merchant.latitude,
                    "items": [],
                    "goods_amount": Decimal("0.00"),
                },
            )

            row_total = cart_item.unit_price_snapshot * cart_item.quantity
            bucket["items"].append(
                {
                    "dish_id": cart_item.dish_id,
                    "dish_name": dish_name,
                    "quantity": cart_item.quantity,
                    "unit_price": cart_item.unit_price_snapshot,
                }
            )
            bucket["goods_amount"] += row_total

        merchant_orders: list[dict] = []
        goods_amount = Decimal("0.00")
        delivery_amount = Decimal("0.00")

        for merchant_order in grouped.values():
            distance_meters = self._distance_meters(
                address.longitude,
                address.latitude,
                merchant_order["merchant_longitude"],
                merchant_order["merchant_latitude"],
            )
            in_range = distance_meters <= merchant_order["merchant_delivery_radius_meters"]
            message = "within delivery range" if in_range else "delivery out of range"
            merchant_delivery_amount = merchant_order["merchant_delivery_fee"] if in_range else Decimal("0.00")
            payable_amount = merchant_order["goods_amount"] + merchant_delivery_amount

            merchant_orders.append(
                {
                    "merchant_id": merchant_order["merchant_id"],
                    "merchant_name": merchant_order["merchant_name"],
                    "min_order_amount": merchant_order["merchant_min_order_amount"],
                    "items": merchant_order["items"],
                    "goods_amount": merchant_order["goods_amount"],
                    "delivery_amount": merchant_delivery_amount,
                    "payable_amount": payable_amount,
                    "delivery_quote": {
                        "merchant_id": merchant_order["merchant_id"],
                        "in_range": in_range,
                        "distance_meters": distance_meters,
                        "estimated_minutes": merchant_order["merchant_avg_delivery_minutes"],
                        "delivery_fee": merchant_delivery_amount,
                        "message": message,
                    },
                }
            )
            goods_amount += merchant_order["goods_amount"]
            delivery_amount += merchant_delivery_amount

        return {
            "address_id": address.id,
            "address_snapshot": self._serialize_address_snapshot(address),
            "merchant_orders": merchant_orders,
            "goods_amount": goods_amount,
            "delivery_amount": delivery_amount,
            "payable_amount": goods_amount + delivery_amount,
        }

    def _serialize_order(self, checkout_order, include_items: bool) -> dict:
        delivery_quotes = {
            quote.merchant_id: quote for quote in self.orders.list_delivery_quotes(checkout_order.id)
        }

        merchant_orders = []
        for merchant_order in self.orders.list_merchant_orders(checkout_order.id):
            merchant = self.carts.get_merchant(merchant_order.merchant_id)
            delivery_quote = delivery_quotes.get(merchant_order.merchant_id)
            merchant_payload = {
                "merchant_order_id": merchant_order.id,
                "merchant_id": merchant_order.merchant_id,
                "merchant_name": merchant.name if merchant else f"merchant-{merchant_order.merchant_id}",
                "goods_amount": float(merchant_order.goods_amount),
                "delivery_amount": float(merchant_order.delivery_amount),
                "payable_amount": float(merchant_order.payable_amount),
                "order_status": merchant_order.order_status,
                "delivery_quote": {
                    "merchant_id": merchant_order.merchant_id,
                    "in_range": delivery_quote.in_range if delivery_quote else True,
                    "distance_meters": delivery_quote.distance_meters if delivery_quote else 0,
                    "estimated_minutes": delivery_quote.estimated_minutes if delivery_quote else 0,
                    "delivery_fee": float(delivery_quote.delivery_fee) if delivery_quote else 0.0,
                    "message": delivery_quote.message if delivery_quote else "",
                },
            }
            if include_items:
                merchant_payload["items"] = [
                    {
                        "dish_id": item.dish_id,
                        "dish_name": item.dish_name_snapshot,
                        "quantity": item.quantity,
                        "unit_price": float(item.unit_price_snapshot),
                    }
                    for item in self.orders.list_order_items(merchant_order.id)
                ]
            merchant_orders.append(merchant_payload)

        return {
            "checkout_order_id": checkout_order.id,
            "address_snapshot": checkout_order.address_snapshot,
            "goods_amount": float(checkout_order.goods_amount),
            "delivery_amount": float(checkout_order.delivery_amount),
            "payable_amount": float(checkout_order.payable_amount),
            "payment_status": checkout_order.payment_status,
            "order_status": checkout_order.order_status,
            "created_at": checkout_order.created_at.isoformat(),
            "merchant_orders": merchant_orders,
        }

    def preview_checkout(self, user_id: int, payload) -> dict:
        preview = self._build_checkout_payload(user_id, payload.address_id)
        return {
            "address_id": preview["address_id"],
            "address_snapshot": preview["address_snapshot"],
            "merchant_orders": [
                {
                    "merchant_id": merchant_order["merchant_id"],
                    "merchant_name": merchant_order["merchant_name"],
                    "items": [
                        {
                            "dish_id": item["dish_id"],
                            "dish_name": item["dish_name"],
                            "quantity": item["quantity"],
                            "unit_price": float(item["unit_price"]),
                        }
                        for item in merchant_order["items"]
                    ],
                    "goods_amount": float(merchant_order["goods_amount"]),
                    "delivery_amount": float(merchant_order["delivery_amount"]),
                    "payable_amount": float(merchant_order["payable_amount"]),
                    "delivery_quote": {
                        **merchant_order["delivery_quote"],
                        "delivery_fee": float(merchant_order["delivery_quote"]["delivery_fee"]),
                    },
                }
                for merchant_order in preview["merchant_orders"]
            ],
            "goods_amount": float(preview["goods_amount"]),
            "delivery_amount": float(preview["delivery_amount"]),
            "payable_amount": float(preview["payable_amount"]),
        }

    def submit_checkout(self, user_id: int, payload) -> dict:
        checkout_payload = self._build_checkout_payload(user_id, payload.address_id)
        for merchant_order in checkout_payload["merchant_orders"]:
            if not merchant_order["delivery_quote"]["in_range"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="delivery out of range")
            if merchant_order["goods_amount"] < merchant_order["min_order_amount"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="minimum order amount not reached",
                )

        checkout_order = self.orders.create_checkout_order(
            user_id=user_id,
            address_snapshot=checkout_payload["address_snapshot"],
            merchant_orders=checkout_payload["merchant_orders"],
        )
        return self._serialize_order(checkout_order, include_items=True)

    def mock_pay(self, user_id: int, payload) -> dict:
        checkout_order = self.orders.mark_paid(
            user_id=user_id,
            checkout_order_id=payload.checkout_order_id,
            request_no=f"mock-{payload.checkout_order_id}-{uuid4().hex[:8]}",
        )
        if checkout_order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order not found")
        return {
            "success": True,
            "checkout_order_id": checkout_order.id,
            "payment_status": checkout_order.payment_status,
            "order_status": checkout_order.order_status,
        }

    def list_orders(self, user_id: int) -> list[dict]:
        return [
            self._serialize_order(checkout_order, include_items=False)
            for checkout_order in self.orders.list_checkout_orders(user_id)
        ]

    def get_order_detail(self, user_id: int, checkout_order_id: int) -> dict:
        checkout_order = self.orders.get_checkout_order_for_user(user_id, checkout_order_id)
        if checkout_order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order not found")
        return self._serialize_order(checkout_order, include_items=True)
