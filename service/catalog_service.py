from sqlalchemy.orm import Session

from repository.catalog_repository import CatalogRepository


class CatalogService:
    def __init__(self, session: Session):
        self.catalog = CatalogRepository(session)

    def list_merchants(self, district: str | None = None) -> list[dict]:
        merchants = self.catalog.list_merchants(district=district)
        return [
            {
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
            for merchant in merchants
        ]

    def list_dishes_by_merchant(self, merchant_id: int) -> list[dict]:
        dishes = self.catalog.list_dishes_by_merchant(merchant_id)
        return [
            {
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
            for dish in dishes
        ]
