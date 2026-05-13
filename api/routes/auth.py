from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.deps import get_current_user
from api.models.user import User
from api.schemas import AuthSessionResponse, CurrentUserResponse, LoginRequest, RefreshTokenRequest, RegisterRequest, TokenPairResponse, UpdateProfileRequest
from service.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, session: Session = Depends(get_db_session)) -> AuthSessionResponse:
    return AuthService(session).register(
        username=request.username,
        password=request.password,
        full_name=request.full_name,
        phone=request.phone,
    )


@router.post("/login", response_model=AuthSessionResponse)
def login(request: LoginRequest, session: Session = Depends(get_db_session)) -> AuthSessionResponse:
    return AuthService(session).login(username=request.username, password=request.password)


@router.post("/refresh", response_model=TokenPairResponse)
def refresh(request: RefreshTokenRequest, session: Session = Depends(get_db_session)) -> TokenPairResponse:
    return AuthService(session).refresh(request.refresh_token)


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> CurrentUserResponse:
    return AuthService(session).current_user(current_user.id)


@router.put("/me", response_model=CurrentUserResponse)
def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> CurrentUserResponse:
    return AuthService(session).update_profile(current_user.id, payload.full_name, payload.phone)
