from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RawMerchant:
    source: str
    source_id: str
    name: str
    city: str
    district: str
    address: str
    longitude: float
    latitude: float
    category: str
    phone: str = ""
    rating: float | None = None
    tags: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RawDish:
    source: str
    source_id: str
    name: str
    description: str
    ingredients: list[str]
    tags: list[str] = field(default_factory=list)
    cuisine_type: str = ""
    price: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedMerchant:
    source: str
    source_id: str
    name: str
    description: str
    city: str
    district: str
    address: str
    longitude: float
    latitude: float
    homepage_category: str
    promo_text: str
    delivery_radius_meters: int
    delivery_fee: float
    min_order_amount: float
    avg_delivery_minutes: int
    rating: float
    phone: str
    business_hours: str
    detailed_address: str
    address_note: str
    merchant_tags: list[str]

    @classmethod
    def from_raw(
        cls,
        raw: RawMerchant,
        *,
        homepage_category: str,
        description: str,
        promo_text: str,
        business_hours: str,
        merchant_tags: list[str],
    ) -> "NormalizedMerchant":
        return cls(
            source=raw.source,
            source_id=raw.source_id,
            name=raw.name,
            description=description,
            city=raw.city,
            district=raw.district,
            address=raw.address,
            longitude=raw.longitude,
            latitude=raw.latitude,
            homepage_category=homepage_category,
            promo_text=promo_text[:64],
            delivery_radius_meters=3000,
            delivery_fee=3.0,
            min_order_amount=20.0,
            avg_delivery_minutes=30,
            rating=min(max(float(raw.rating or 4.5), 3.5), 5.0),
            phone=raw.phone,
            business_hours=business_hours,
            detailed_address=raw.address,
            address_note=f"{raw.district} pickup and delivery area",
            merchant_tags=merchant_tags[:5],
        )


@dataclass(frozen=True)
class NormalizedDish:
    source: str
    source_id: str
    name: str
    description: str
    price: float
    tags: list[str]
    cuisine_type: str
    flavor_profile: str
    ingredients: list[str]
    allergens: list[str]
    cooking_method: str
    is_recommended: bool

    @classmethod
    def from_raw(
        cls,
        raw: RawDish,
        *,
        cuisine_type: str,
        flavor_profile: str,
        cooking_method: str,
        allergens: list[str],
        price: float,
        is_recommended: bool,
    ) -> "NormalizedDish":
        return cls(
            source=raw.source,
            source_id=raw.source_id,
            name=raw.name,
            description=raw.description,
            price=round(float(price), 2),
            tags=list(dict.fromkeys([*raw.tags, cuisine_type, flavor_profile])),
            cuisine_type=cuisine_type,
            flavor_profile=flavor_profile,
            ingredients=list(raw.ingredients),
            allergens=list(allergens),
            cooking_method=cooking_method,
            is_recommended=is_recommended,
        )


@dataclass(frozen=True)
class DishAssignment:
    merchant: NormalizedMerchant
    category_name: str
    dishes: list[NormalizedDish]


@dataclass(frozen=True)
class ImportSummary:
    merchants_seen: int
    merchants_written: int
    dishes_seen: int
    dishes_written: int
    categories_written: int
