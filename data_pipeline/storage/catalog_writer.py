from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.catalog import Dish, DishCategory, Merchant
from data_pipeline.models import DishAssignment, ImportSummary, NormalizedDish, NormalizedMerchant


class CatalogWriter:
    def __init__(self, session: Session) -> None:
        self.session = session

    def write(self, assignments: list[DishAssignment]) -> ImportSummary:
        merchants_seen = len(assignments)
        dishes_seen = sum(len(assignment.dishes) for assignment in assignments)
        merchants_written = 0
        categories_written = 0
        dishes_written = 0

        for assignment in assignments:
            merchant, created = self._get_or_create_merchant(assignment.merchant)
            if created:
                merchants_written += 1
            category, category_created = self._get_or_create_category(merchant.id, assignment.category_name)
            if category_created:
                categories_written += 1
            for normalized_dish in assignment.dishes:
                if self._dish_exists(merchant.id, normalized_dish.name):
                    continue
                self.session.add(self._build_dish(merchant.id, category.id, normalized_dish))
                dishes_written += 1

        self.session.commit()
        return ImportSummary(
            merchants_seen=merchants_seen,
            merchants_written=merchants_written,
            dishes_seen=dishes_seen,
            dishes_written=dishes_written,
            categories_written=categories_written,
        )

    def _get_or_create_merchant(self, normalized: NormalizedMerchant) -> tuple[Merchant, bool]:
        statement = select(Merchant).where(
            Merchant.name == normalized.name,
            Merchant.district == normalized.district,
            Merchant.address == normalized.address,
        )
        existing = self.session.scalar(statement)
        if existing is not None:
            return existing, False
        merchant = Merchant(
            name=normalized.name[:128],
            description=normalized.description,
            city=normalized.city[:64],
            district=normalized.district[:64],
            address=normalized.address,
            longitude=normalized.longitude,
            latitude=normalized.latitude,
            homepage_category=normalized.homepage_category[:32],
            promo_text=normalized.promo_text[:64],
            delivery_radius_meters=normalized.delivery_radius_meters,
            delivery_fee=Decimal(str(normalized.delivery_fee)),
            min_order_amount=Decimal(str(normalized.min_order_amount)),
            avg_delivery_minutes=normalized.avg_delivery_minutes,
            rating=Decimal(str(normalized.rating)),
            phone=normalized.phone[:32],
            business_hours=normalized.business_hours[:64],
            detailed_address=normalized.detailed_address,
            address_note=normalized.address_note[:128],
            merchant_tags=normalized.merchant_tags,
        )
        self.session.add(merchant)
        self.session.flush()
        return merchant, True

    def _get_or_create_category(self, merchant_id: int, name: str) -> tuple[DishCategory, bool]:
        statement = select(DishCategory).where(DishCategory.merchant_id == merchant_id, DishCategory.name == name)
        existing = self.session.scalar(statement)
        if existing is not None:
            return existing, False
        category = DishCategory(merchant_id=merchant_id, name=name, sort_order=1)
        self.session.add(category)
        self.session.flush()
        return category, True

    def _dish_exists(self, merchant_id: int, name: str) -> bool:
        statement = select(Dish.id).where(Dish.merchant_id == merchant_id, Dish.name == name)
        return self.session.scalar(statement) is not None

    @staticmethod
    def _build_dish(merchant_id: int, category_id: int, normalized: NormalizedDish) -> Dish:
        return Dish(
            merchant_id=merchant_id,
            category_id=category_id,
            name=normalized.name[:128],
            description=normalized.description[:500],
            price=Decimal(str(normalized.price)),
            tags=",".join(normalized.tags)[:255],
            cuisine_type=normalized.cuisine_type,
            flavor_profile=normalized.flavor_profile,
            ingredients=normalized.ingredients,
            allergens=normalized.allergens,
            cooking_method=normalized.cooking_method,
            is_recommended=normalized.is_recommended,
            is_available=True,
        )
