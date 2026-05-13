import json

from fastapi import APIRouter, Depends, status
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.deps import get_current_user, get_current_user_ws
from api.models.user import User
from api.schemas import (
    CheckoutOrderDetailResponse,
    CheckoutOrderSummaryResponse,
    CheckoutPreviewRequest,
    CheckoutPreviewResponse,
    MockPayRequest,
    MockPayResponse,
    OrderReviewRequest,
    OrderReviewResponse,
    ReorderResponse,
)
from service.order_events import subscribe
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


@router.post("/{checkout_order_id}/advance", response_model=CheckoutOrderDetailResponse)
def advance_order_status(
    checkout_order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> CheckoutOrderDetailResponse:
    return OrderService(session).advance_order_status(current_user.id, checkout_order_id)


@router.post("/{checkout_order_id}/cancel", response_model=CheckoutOrderDetailResponse)
def cancel_order(
    checkout_order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> CheckoutOrderDetailResponse:
    return OrderService(session).cancel_order(current_user.id, checkout_order_id)


@router.post("/{checkout_order_id}/review", response_model=OrderReviewResponse, status_code=status.HTTP_201_CREATED)
def submit_review(
    checkout_order_id: int,
    payload: OrderReviewRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> OrderReviewResponse:
    return OrderService(session).submit_review(current_user.id, checkout_order_id, payload)


@router.get("/{checkout_order_id}/review", response_model=OrderReviewResponse | None)
def get_review(
    checkout_order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> OrderReviewResponse | None:
    return OrderService(session).get_review(current_user.id, checkout_order_id)


@router.post("/{checkout_order_id}/reorder", response_model=ReorderResponse)
def reorder(
    checkout_order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> ReorderResponse:
    return OrderService(session).reorder(current_user.id, checkout_order_id)


@router.get("/{checkout_order_id}/events")
async def order_events(
    checkout_order_id: int,
    current_user: User = Depends(get_current_user_ws),
):
    async def event_generator():
        async for event in subscribe(checkout_order_id):
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]),
            }

    return EventSourceResponse(event_generator())


@router.get("/{checkout_order_id}", response_model=CheckoutOrderDetailResponse)
def get_order_detail(
    checkout_order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> CheckoutOrderDetailResponse:
    return OrderService(session).get_order_detail(current_user.id, checkout_order_id)
