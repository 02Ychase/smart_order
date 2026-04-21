from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.deps import get_current_user
from api.models.user import User
from api.schemas import (
    CheckoutOrderDetailResponse,
    CheckoutOrderSummaryResponse,
    CheckoutPreviewRequest,
    CheckoutPreviewResponse,
    MockPayRequest,
    MockPayResponse,
)
from service.order_service import OrderService


router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/preview", response_model=CheckoutPreviewResponse)
def preview_checkout(
    payload: CheckoutPreviewRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> CheckoutPreviewResponse:
    return OrderService(session).preview_checkout(current_user.id, payload)


@router.get("", response_model=list[CheckoutOrderSummaryResponse])
def list_orders(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> list[CheckoutOrderSummaryResponse]:
    return OrderService(session).list_orders(current_user.id)


@router.post("", response_model=CheckoutOrderDetailResponse, status_code=status.HTTP_201_CREATED)
def submit_checkout(
    payload: CheckoutPreviewRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> CheckoutOrderDetailResponse:
    return OrderService(session).submit_checkout(current_user.id, payload)


@router.post("/mock-pay", response_model=MockPayResponse)
def mock_pay(
    payload: MockPayRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> MockPayResponse:
    return OrderService(session).mock_pay(current_user.id, payload)


@router.get("/{checkout_order_id}", response_model=CheckoutOrderDetailResponse)
def get_order_detail(
    checkout_order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> CheckoutOrderDetailResponse:
    return OrderService(session).get_order_detail(current_user.id, checkout_order_id)
