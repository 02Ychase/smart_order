from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.coupon import Coupon


class CouponRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_by_user(self, user_id: int) -> list[Coupon]:
        statement = (
            select(Coupon)
            .where(Coupon.user_id == user_id)
            .order_by(Coupon.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def get_by_code(self, code: str) -> Coupon | None:
        statement = select(Coupon).where(Coupon.code == code)
        return self.session.scalar(statement)

    def claim(self, user_id: int, code: str, discount_amount: float, min_order_amount: float, expires_at: datetime | None) -> Coupon:
        coupon = Coupon(
            user_id=user_id,
            code=code,
            discount_amount=discount_amount,
            min_order_amount=min_order_amount,
            expires_at=expires_at,
        )
        self.session.add(coupon)
        self.session.commit()
        self.session.refresh(coupon)
        return coupon
