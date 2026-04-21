from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.deps import get_current_user
from api.models.user import User
from api.schemas import CartMutationRequest
from service.cart_service import CartService


router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("")
def get_cart(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return CartService(session).get_grouped_cart(current_user.id)


@router.post("/items")
def add_item(
    payload: CartMutationRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return CartService(session).add_item(current_user.id, payload)


@router.delete("/items/{dish_id}")
def remove_item(
    dish_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return CartService(session).remove_item(current_user.id, dish_id)
