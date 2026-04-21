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
