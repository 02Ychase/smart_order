from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class CheckoutOrder(Base):
    __tablename__ = "checkout_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    address_snapshot: Mapped[str] = mapped_column(Text)
    goods_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    delivery_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    payment_status: Mapped[str] = mapped_column(String(32), default="pending_payment")
    order_status: Mapped[str] = mapped_column(String(32), default="pending_payment")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MerchantOrder(Base):
    __tablename__ = "merchant_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkout_order_id: Mapped[int] = mapped_column(ForeignKey("checkout_orders.id"), index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    goods_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    delivery_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    order_status: Mapped[str] = mapped_column(String(32), default="pending_payment")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_order_id: Mapped[int] = mapped_column(ForeignKey("merchant_orders.id"), index=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id"), index=True)
    dish_name_snapshot: Mapped[str] = mapped_column(String(128))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2))


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkout_order_id: Mapped[int] = mapped_column(ForeignKey("checkout_orders.id"), index=True)
    channel: Mapped[str] = mapped_column(String(32), default="mock")
    request_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    payment_status: Mapped[str] = mapped_column(String(32), default="succeeded")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DeliveryQuote(Base):
    __tablename__ = "delivery_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkout_order_id: Mapped[int] = mapped_column(ForeignKey("checkout_orders.id"), index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    in_range: Mapped[bool] = mapped_column(Boolean, default=True)
    distance_meters: Mapped[int] = mapped_column(Integer, default=0)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=0)
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    message: Mapped[str] = mapped_column(Text, default="")


class OrderReview(Base):
    __tablename__ = "order_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkout_order_id: Mapped[int] = mapped_column(ForeignKey("checkout_orders.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
