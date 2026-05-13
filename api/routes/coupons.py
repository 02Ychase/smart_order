from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.deps import get_current_user
from api.models.user import User
from api.schemas import ClaimCouponRequest, CouponResponse
from service.coupon_service import CouponService


router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.get("", response_model=list[CouponResponse])
def list_coupons(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> list[CouponResponse]:
    return CouponService(session).list_coupons(current_user.id)


@router.post("/claim", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
def claim_coupon(
    payload: ClaimCouponRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> CouponResponse:
    return CouponService(session).claim_coupon(current_user.id, payload.code)
