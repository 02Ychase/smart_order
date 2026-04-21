from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.schemas import DishResponse, MerchantSummaryResponse
from service.catalog_service import CatalogService


router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/merchants", response_model=list[MerchantSummaryResponse])
def list_merchants(
    district: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
) -> list[MerchantSummaryResponse]:
    return CatalogService(session).list_merchants(district=district)


@router.get("/merchants/{merchant_id}/dishes", response_model=list[DishResponse])
def list_dishes_by_merchant(
    merchant_id: int,
    session: Session = Depends(get_db_session),
) -> list[DishResponse]:
    return CatalogService(session).list_dishes_by_merchant(merchant_id)
