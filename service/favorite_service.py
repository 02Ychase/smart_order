from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repository.catalog_repository import CatalogRepository
from repository.favorite_repository import FavoriteRepository


class FavoriteService:
    def __init__(self, session: Session):
        self.favorites = FavoriteRepository(session)
        self.catalog = CatalogRepository(session)

    def list_favorites(self, user_id: int) -> list[dict]:
        results: list[dict] = []
        for fav in self.favorites.list_by_user(user_id):
            merchant = self.catalog.get_merchant(fav.merchant_id)
            results.append({
                "id": fav.id,
                "merchant_id": fav.merchant_id,
                "merchant_name": merchant.name if merchant else f"merchant-{fav.merchant_id}",
                "created_at": fav.created_at.isoformat(),
            })
        return results

    def toggle_favorite(self, user_id: int, merchant_id: int) -> dict:
        existing = self.favorites.get(user_id, merchant_id)
        if existing is not None:
            self.favorites.remove(user_id, merchant_id)
            return {"favorited": False, "merchant_id": merchant_id}

        merchant = self.catalog.get_merchant(merchant_id)
        if merchant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="merchant not found")

        self.favorites.add(user_id, merchant_id)
        return {"favorited": True, "merchant_id": merchant_id}

    def is_favorited(self, user_id: int, merchant_id: int) -> bool:
        return self.favorites.get(user_id, merchant_id) is not None
