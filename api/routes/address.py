from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.deps import get_current_user
from api.models.user import User
from api.schemas import AddressActionResponse, AddressRequest, AddressResponse
from service.user_profile_service import UserProfileService


router = APIRouter(prefix="/addresses", tags=["addresses"])


@router.get("", response_model=list[AddressResponse])
def list_addresses(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> list[AddressResponse]:
    return UserProfileService(session).list_addresses(current_user.id)


@router.post("", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
def create_address(
    payload: AddressRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> AddressResponse:
    return UserProfileService(session).create_address(current_user.id, payload)


@router.put("/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: int,
    payload: AddressRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> AddressResponse:
    return UserProfileService(session).update_address(current_user.id, address_id, payload)


@router.post("/{address_id}/default", response_model=AddressActionResponse)
def set_default_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> AddressActionResponse:
    return UserProfileService(session).set_default_address(current_user.id, address_id)


@router.delete("/{address_id}", response_model=AddressActionResponse)
def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> AddressActionResponse:
    return UserProfileService(session).delete_address(current_user.id, address_id)
