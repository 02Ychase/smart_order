from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from api.schemas import AddressResponse, AuthSessionResponse, CurrentUserResponse, TokenPairResponse
from api.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from repository.user_repository import UserRepository


class AuthService:
    def __init__(self, session: Session):
        self.users = UserRepository(session)

    def _serialize_user(self, user) -> CurrentUserResponse:
        return CurrentUserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            phone=user.phone,
        )

    def _serialize_address(self, address) -> AddressResponse:
        return AddressResponse(
            id=address.id,
            label=address.label,
            contact_name=address.contact_name,
            contact_phone=address.contact_phone,
            city=address.city,
            district=address.district,
            detail_address=address.detail_address,
            longitude=address.longitude,
            latitude=address.latitude,
            is_default=address.is_default,
        )

    def _build_session_response(self, user) -> AuthSessionResponse:
        return AuthSessionResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
            user=self._serialize_user(user),
            addresses=[
                self._serialize_address(address)
                for address in self.users.list_addresses(user.id)
            ],
        )

    def register(self, username: str, password: str, full_name: str, phone: str) -> AuthSessionResponse:
        if self.users.get_by_username(username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username already exists")

        user = self.users.create_user(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            phone=phone,
        )
        return self._build_session_response(user)

    def login(self, username: str, password: str) -> AuthSessionResponse:
        user = self.users.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

        return self._build_session_response(user)

    def refresh(self, refresh_token: str) -> TokenPairResponse:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise ValueError("invalid refresh token")
            user_id = int(payload["sub"])
        except (ValueError, KeyError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token")

        user = self.users.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")

        return TokenPairResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )

    def current_user(self, user_id: int) -> CurrentUserResponse:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
        return self._serialize_user(user)

    def update_profile(self, user_id: int, full_name: str, phone: str) -> CurrentUserResponse:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
        user.full_name = full_name
        user.phone = phone
        self.users.session.commit()
        self.users.session.refresh(user)
        return self._serialize_user(user)
