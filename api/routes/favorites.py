from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.deps import get_current_user
from api.models.user import User
from api.schemas import FavoriteResponse, FavoriteToggleResponse
from service.favorite_service import FavoriteService


router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[FavoriteResponse])
def list_favorites(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> list[FavoriteResponse]:
    return FavoriteService(session).list_favorites(current_user.id)


@router.post("/{merchant_id}/toggle", response_model=FavoriteToggleResponse)
def toggle_favorite(
    merchant_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> FavoriteToggleResponse:
    return FavoriteService(session).toggle_favorite(current_user.id, merchant_id)


@router.get("/{merchant_id}/status")
def check_favorite(
    merchant_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> dict:
    favorited = FavoriteService(session).is_favorited(current_user.id, merchant_id)
    return {"favorited": favorited, "merchant_id": merchant_id}
