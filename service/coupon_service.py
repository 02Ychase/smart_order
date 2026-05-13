from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repository.coupon_repository import CouponRepository

COUPON_TEMPLATES: dict[str, dict] = {
    "WELCOME5": {"discount_amount": 5.0, "min_order_amount": 20.0},
    "SAVE10": {"discount_amount": 10.0, "min_order_amount": 50.0},
}


class CouponService:
    def __init__(self, session: Session):
        self.coupons = CouponRepository(session)

    def list_coupons(self, user_id: int) -> list[dict]:
        return [
            {
                "id": coupon.id,
                "code": coupon.code,
                "discount_amount": float(coupon.discount_amount),
                "min_order_amount": float(coupon.min_order_amount),
                "status": coupon.status,
                "expires_at": coupon.expires_at.isoformat() if coupon.expires_at else None,
                "created_at": coupon.created_at.isoformat(),
            }
            for coupon in self.coupons.list_by_user(user_id)
        ]

    def claim_coupon(self, user_id: int, code: str) -> dict:
        template = COUPON_TEMPLATES.get(code)
        if template is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="优惠券码不存在")

        existing = self.coupons.get_by_code(code)
        if existing is not None and existing.user_id == user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="优惠券已领取")

        coupon = self.coupons.claim(
            user_id=user_id,
            code=code,
            discount_amount=template["discount_amount"],
            min_order_amount=template["min_order_amount"],
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        return {
            "id": coupon.id,
            "code": coupon.code,
            "discount_amount": float(coupon.discount_amount),
            "min_order_amount": float(coupon.min_order_amount),
            "status": coupon.status,
            "expires_at": coupon.expires_at.isoformat() if coupon.expires_at else None,
            "created_at": coupon.created_at.isoformat(),
        }
