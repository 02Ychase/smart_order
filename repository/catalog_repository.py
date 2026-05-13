from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.catalog import Dish, Merchant


class CatalogRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_merchants(self, district: str | None = None) -> list[Merchant]:
        statement = (
            select(Merchant)
            .where(Merchant.is_open.is_(True))
            .order_by(Merchant.rating.desc(), Merchant.id.asc())
        )
        if district:
            statement = statement.where(Merchant.district == district)
        return list(self.session.scalars(statement))

    def list_dishes_by_merchant(self, merchant_id: int) -> list[Dish]:
        statement = (
            select(Dish)
            .where(Dish.merchant_id == merchant_id, Dish.is_available.is_(True))
            .order_by(Dish.is_recommended.desc(), Dish.id.asc())
        )
        return list(self.session.scalars(statement))

    def list_dishes_filtered(
        self,
        cuisine_types: list[str] | None = None,
        flavor_keywords: list[str] | None = None,
        required_keywords: list[str] | None = None,
        forbidden_keywords: list[str] | None = None,
        merchant_id: int | None = None,
        limit: int = 100,
    ) -> list[Dish]:
        statement = (
            select(Dish)
            .join(Merchant)
            .where(Dish.is_available.is_(True), Merchant.is_open.is_(True))
        )
        if merchant_id is not None:
            statement = statement.where(Dish.merchant_id == merchant_id)
        if cuisine_types:
            statement = statement.where(Dish.cuisine_type.in_(cuisine_types))
        if flavor_keywords:
            for kw in flavor_keywords:
                statement = statement.where(
                    Dish.flavor_profile.contains(kw) | Dish.name.contains(kw) | Dish.description.contains(kw)
                )
        if required_keywords:
            for kw in required_keywords:
                statement = statement.where(
                    Dish.name.contains(kw) | Dish.description.contains(kw) | Dish.tags.contains(kw)
                )
        if forbidden_keywords:
            for kw in forbidden_keywords:
                statement = statement.where(
                    ~(Dish.name.contains(kw) | Dish.description.contains(kw) | Dish.tags.contains(kw))
                )
        return list(
            self.session.scalars(
                statement.order_by(Dish.is_recommended.desc(), Dish.id.asc()).limit(limit)
            )
        )

    def list_recommended_dishes(self, limit: int = 50) -> list[Dish]:
        statement = (
            select(Dish)
            .join(Merchant)
            .where(
                Dish.is_recommended.is_(True),
                Dish.is_available.is_(True),
                Merchant.is_open.is_(True),
            )
            .order_by(Merchant.rating.desc(), Dish.id.asc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_merchants_filtered(
        self,
        cuisine_types: list[str] | None = None,
        required_keywords: list[str] | None = None,
        limit: int = 50,
    ) -> list[Merchant]:
        statement = (
            select(Merchant)
            .where(Merchant.is_open.is_(True))
            .order_by(Merchant.rating.desc(), Merchant.id.asc())
        )
        if cuisine_types:
            statement = statement.where(Merchant.homepage_category.in_(cuisine_types))
        if required_keywords:
            for kw in required_keywords:
                statement = statement.where(
                    Merchant.name.contains(kw)
                    | Merchant.description.contains(kw)
                    | Merchant.homepage_category.contains(kw)
                )
        return list(self.session.scalars(statement.limit(limit)))

    def get_merchant(self, merchant_id: int) -> Merchant | None:
        return self.session.get(Merchant, merchant_id)

    def search_merchants(self, keyword: str, limit: int = 20) -> list[Merchant]:
        pattern = f"%{keyword}%"
        statement = (
            select(Merchant)
            .where(
                Merchant.is_open.is_(True),
                Merchant.name.ilike(pattern) | Merchant.description.ilike(pattern),
            )
            .order_by(Merchant.rating.desc(), Merchant.id.asc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def search_dishes(self, keyword: str, limit: int = 20) -> list[Dish]:
        pattern = f"%{keyword}%"
        statement = (
            select(Dish)
            .join(Merchant)
            .where(
                Dish.is_available.is_(True),
                Merchant.is_open.is_(True),
                Dish.name.ilike(pattern) | Dish.description.ilike(pattern) | Dish.tags.ilike(pattern),
            )
            .order_by(Dish.is_recommended.desc(), Dish.id.asc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))
