import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

TEST_DATABASE_PATH = Path("test_auth_routes.db")
TEST_DATABASE_PATH.unlink(missing_ok=True)

os.environ["JWT_SECRET_KEY"] = "test-phase1-secret"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

from api.db import engine
from api.main import app
from api.models.user import User, UserAddress
from api.security import hash_password


User.__table__.create(bind=engine, checkfirst=True)
UserAddress.__table__.create(bind=engine, checkfirst=True)
client = TestClient(app, raise_server_exceptions=False)


def test_register_persists_user_and_returns_session_payload() -> None:
    register_response = client.post(
        "/auth/register",
        json={
            "username": "phase1_user",
            "password": "strong-password",
            "full_name": "Phase One User",
            "phone": "13800000000",
        },
    )

    assert register_response.status_code == 201
    payload = register_response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["token_type"] == "bearer"
    assert payload["user"]["username"] == "phase1_user"
    assert payload["user"]["full_name"] == "Phase One User"
    assert payload["user"]["phone"] == "13800000000"
    assert payload["addresses"] == []

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "phase1_user"

    with Session(engine) as session:
        stored_user = session.scalar(select(User).where(User.username == "phase1_user"))
        assert stored_user is not None
        assert payload["user"]["id"] == stored_user.id
        assert stored_user.full_name == "Phase One User"
        assert stored_user.phone == "13800000000"
        assert stored_user.password_hash != "strong-password"


def test_register_rejects_duplicate_username() -> None:
    first_response = client.post(
        "/auth/register",
        json={
            "username": "duplicate_user",
            "password": "strong-password",
            "full_name": "Duplicate User",
            "phone": "13800000001",
        },
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/auth/register",
        json={
            "username": "duplicate_user",
            "password": "strong-password",
            "full_name": "Duplicate User",
            "phone": "13800000001",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "username already exists"


def test_login_returns_session_payload_with_saved_addresses() -> None:
    with Session(engine) as session:
        user = User(
            username="saved_user",
            password_hash=hash_password("strong-password"),
            full_name="Saved User",
            phone="13800000002",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        address = UserAddress(
            user_id=user.id,
            label="家",
            contact_name="李四",
            contact_phone="13800000002",
            city="上海",
            district="静安",
            detail_address="南京西路 100 号 1 室",
            longitude=121.4737,
            latitude=31.2304,
            is_default=True,
        )
        session.add(address)
        session.commit()
        session.refresh(address)

    login_response = client.post(
        "/auth/login",
        json={"username": "saved_user", "password": "strong-password"},
    )

    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["username"] == "saved_user"
    assert payload["addresses"] == [
        {
            "id": address.id,
            "label": "家",
            "contact_name": "李四",
            "contact_phone": "13800000002",
            "city": "上海",
            "district": "静安",
            "detail_address": "南京西路 100 号 1 室",
            "longitude": 121.4737,
            "latitude": 31.2304,
            "is_default": True,
        }
    ]


def test_refresh_keeps_returning_token_pair() -> None:
    with Session(engine) as session:
        user = User(
            username="refresh_user",
            password_hash=hash_password("strong-password"),
            full_name="Refresh User",
            phone="13800000003",
        )
        session.add(user)
        session.commit()

    login_response = client.post(
        "/auth/login",
        json={"username": "refresh_user", "password": "strong-password"},
    )
    assert login_response.status_code == 200

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": login_response.json()["refresh_token"]},
    )

    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()
    assert refresh_payload["access_token"]
    assert refresh_payload["refresh_token"]
    assert refresh_payload["token_type"] == "bearer"
