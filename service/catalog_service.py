from sqlalchemy.orm import Session

from repository.catalog_repository import CatalogRepository


class CatalogService:
    def __init__(self, session: Session):
        self.catalog = CatalogRepository(session)

    def list_merchants(self, district: str | None = None) -> list[dict]:
        merchants = self.catalog.list_merchants(district=district)
        return [_serialize_merchant(m) for m in merchants]

    def list_dishes_by_merchant(self, merchant_id: int) -> list[dict]:
        dishes = self.catalog.list_dishes_by_merchant(merchant_id)
        return [_serialize_dish(d) for d in dishes]

    def list_dishes_filtered(
        self,
        cuisine_types: list[str] | None = None,
        flavor_keywords: list[str] | None = None,
        required_keywords: list[str] | None = None,
        forbidden_keywords: list[str] | None = None,
        merchant_id: int | None = None,
        limit: int = 100,
    ) -> list[dict]:
        dishes = self.catalog.list_dishes_filtered(
            cuisine_types=cuisine_types,
            flavor_keywords=flavor_keywords,
            required_keywords=required_keywords,
            forbidden_keywords=forbidden_keywords,
            merchant_id=merchant_id,
            limit=limit,
        )
        return [_serialize_dish(d) for d in dishes]

    def list_recommended_dishes(self, limit: int = 50) -> list[dict]:
        dishes = self.catalog.list_recommended_dishes(limit=limit)
        return [_serialize_dish(d) for d in dishes]

    def list_merchants_filtered(
        self,
        cuisine_types: list[str] | None = None,
        required_keywords: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict]:
        merchants = self.catalog.list_merchants_filtered(
            cuisine_types=cuisine_types,
            required_keywords=required_keywords,
            limit=limit,
        )
        return [_serialize_merchant(m) for m in merchants]

    def get_merchant(self, merchant_id: int) -> dict | None:
        merchant = self.catalog.get_merchant(merchant_id)
        if merchant is None:
            return None
        return _serialize_merchant(merchant)


def _serialize_merchant(merchant) -> dict:
    return {
        "id": merchant.id,
        "name": merchant.name,
        "description": merchant.description,
        "district": merchant.district,
        "homepage_category": merchant.homepage_category,
        "promo_text": merchant.promo_text or merchant.description,
        "delivery_fee": float(merchant.delivery_fee),
        "min_order_amount": float(merchant.min_order_amount),
        "avg_delivery_minutes": merchant.avg_delivery_minutes,
        "rating": float(merchant.rating),
        "phone": merchant.phone,
        "business_hours": merchant.business_hours,
        "detailed_address": merchant.detailed_address,
        "address_note": merchant.address_note,
        "merchant_tags": list(merchant.merchant_tags or []),
    }


def _serialize_dish(dish) -> dict:
    return {
        "id": dish.id,
        "merchant_id": dish.merchant_id,
        "category_id": dish.category_id,
        "name": dish.name,
        "description": dish.description,
        "price": float(dish.price),
        "tags": [tag for tag in dish.tags.split(",") if tag],
        "is_recommended": dish.is_recommended,
        "cuisine_type": dish.cuisine_type,
        "flavor_profile": dish.flavor_profile,
        "ingredients": list(dish.ingredients or []),
        "allergens": list(dish.allergens or []),
        "cooking_method": dish.cooking_method,
    }
