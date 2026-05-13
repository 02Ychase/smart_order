from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.schemas import DishResponse, MerchantSummaryResponse, SearchResponse
from service.catalog_service import CatalogService


router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/merchants", response_model=list[MerchantSummaryResponse])
def list_merchants(
    district: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
) -> list[MerchantSummaryResponse]:
    return CatalogService(session).list_merchants(district=district)


@router.get("/merchants/{merchant_id}", response_model=MerchantSummaryResponse)
def get_merchant(
    merchant_id: int,
    session: Session = Depends(get_db_session),
) -> MerchantSummaryResponse:
    result = CatalogService(session).get_merchant(merchant_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="merchant not found")
    return result


@router.get("/merchants/{merchant_id}/dishes", response_model=list[DishResponse])
def list_dishes_by_merchant(
    merchant_id: int,
    session: Session = Depends(get_db_session),
) -> list[DishResponse]:
    return CatalogService(session).list_dishes_by_merchant(merchant_id)


@router.get("/search", response_model=SearchResponse)
def search_catalog(
    keyword: str = Query(min_length=1),
    session: Session = Depends(get_db_session),
) -> SearchResponse:
    return CatalogService(session).search(keyword)
