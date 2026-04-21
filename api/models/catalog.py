from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(64))
    district: Mapped[str] = mapped_column(String(64))
    address: Mapped[str] = mapped_column(Text)
    longitude: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    homepage_category: Mapped[str] = mapped_column(String(32), default="全部", index=True)
    promo_text: Mapped[str] = mapped_column(String(64), default="")
    delivery_radius_meters: Mapped[int] = mapped_column(Integer, default=3000)
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    min_order_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    avg_delivery_minutes: Mapped[int] = mapped_column(Integer, default=30)
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=4.5)
    phone: Mapped[str] = mapped_column(String(32), default="")
    business_hours: Mapped[str] = mapped_column(String(64), default="")
    detailed_address: Mapped[str] = mapped_column(Text, default="")
    address_note: Mapped[str] = mapped_column(String(128), default="")
    merchant_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    categories: Mapped[list["DishCategory"]] = relationship(back_populates="merchant", cascade="all, delete-orphan")
    dishes: Mapped[list["Dish"]] = relationship(back_populates="merchant", cascade="all, delete-orphan")


class DishCategory(Base):
    __tablename__ = "dish_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    merchant: Mapped[Merchant] = relationship(back_populates="categories")
    dishes: Mapped[list["Dish"]] = relationship(back_populates="category")


class Dish(Base):
    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("dish_categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    image_url: Mapped[str] = mapped_column(String(255), default="")
    tags: Mapped[str] = mapped_column(String(255), default="")
    cuisine_type: Mapped[str] = mapped_column(String(64), default="")
    flavor_profile: Mapped[str] = mapped_column(String(64), default="")
    ingredients: Mapped[list[str]] = mapped_column(JSON, default=list)
    allergens: Mapped[list[str]] = mapped_column(JSON, default=list)
    cooking_method: Mapped[str] = mapped_column(String(64), default="")
    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    merchant: Mapped[Merchant] = relationship(back_populates="dishes")
    category: Mapped[DishCategory] = relationship(back_populates="dishes")
