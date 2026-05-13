from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.favorite import Favorite


class FavoriteRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_by_user(self, user_id: int) -> list[Favorite]:
        statement = (
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def get(self, user_id: int, merchant_id: int) -> Favorite | None:
        statement = select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.merchant_id == merchant_id,
        )
        return self.session.scalar(statement)

    def add(self, user_id: int, merchant_id: int) -> Favorite:
        favorite = Favorite(user_id=user_id, merchant_id=merchant_id)
        self.session.add(favorite)
        self.session.commit()
        self.session.refresh(favorite)
        return favorite

    def remove(self, user_id: int, merchant_id: int) -> bool:
        favorite = self.get(user_id, merchant_id)
        if favorite is None:
            return False
        self.session.delete(favorite)
        self.session.commit()
        return True
