# Auth and Address Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make registration persist users and auto-login, make login validate against stored users and return token + user + addresses, and keep multi-address management fully database-backed for each authenticated user.

**Architecture:** Keep the existing `auth` and `addresses` route split, preserve the current `User` and `UserAddress` tables, and add one unified auth session response at the schema/service boundary. `AuthService` becomes responsible for composing `access_token`, `refresh_token`, `user`, and `addresses`, while the existing address repository and address routes continue to own address CRUD and user scoping.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Passlib bcrypt, JOSE JWT, pytest, SQLite test database

---

## File Map

- Modify: `api/schemas.py`
  - Add a session response schema that combines tokens, current user data, and address list while preserving the existing `TokenPairResponse` for refresh.
- Modify: `service/auth_service.py`
  - Compose the new session response for register/login and serialize addresses from persisted `UserAddress` rows.
- Modify: `api/routes/auth.py`
  - Switch `POST /auth/register` and `POST /auth/login` to the new response model.
- Verify: `api/routes/address.py`
  - No design-driven code change expected; existing route structure should remain.
- Verify: `service/user_profile_service.py`
  - No design-driven code change expected; it already serializes the canonical address payload.
- Verify: `repository/user_repository.py`
  - No design-driven code change expected; it already persists users and user-scoped addresses.
- Verify: `api/models/user.py`
  - No design-driven code change expected; the required columns and relationships already exist.
- Modify: `tests/api/test_auth_routes.py`
  - Replace the current token-only happy-path test with persistence-backed auth session contract tests.
- Modify: `tests/api/test_address_routes.py`
  - Replace monkeypatched CRUD assertions with real auth + real DB address integration tests.

### Task 1: Lock the new auth session contract with failing API tests

**Files:**
- Modify: `tests/api/test_auth_routes.py`
- Test: `tests/api/test_auth_routes.py`

- [ ] **Step 1: Replace the imports and table setup so auth tests can inspect persisted users and addresses**

Replace the top of `tests/api/test_auth_routes.py` with this block:

```python
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
```

- [ ] **Step 2: Replace the current auth round-trip test with a failing registration session test**

Replace the existing `test_register_login_refresh_and_current_user_round_trip` function in `tests/api/test_auth_routes.py` with this test:

```python
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
    assert payload["user"] == {
        "id": 1,
        "username": "phase1_user",
        "full_name": "Phase One User",
        "phone": "13800000000",
    }
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
        assert stored_user.full_name == "Phase One User"
        assert stored_user.phone == "13800000000"
        assert stored_user.password_hash != "strong-password"
```

- [ ] **Step 3: Add a duplicate-username regression test**

Append this test to `tests/api/test_auth_routes.py`:

```python
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
```

- [ ] **Step 4: Add a failing login test that requires saved addresses in the auth response**

Append this test to `tests/api/test_auth_routes.py`:

```python
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

        session.add(
            UserAddress(
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
        )
        session.commit()

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
            "id": 1,
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
```

- [ ] **Step 5: Keep refresh behavior covered**

Append this test to `tests/api/test_auth_routes.py`:

```python
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
```

- [ ] **Step 6: Run the auth route tests to verify the new session-contract assertions fail for the expected reason**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/api/test_auth_routes.py -q
```

Expected:
- FAIL because `/auth/register` still returns `CurrentUserResponse` instead of a session payload
- FAIL because `/auth/login` still returns `TokenPairResponse` without `user` and `addresses`
- PASS or remain compatible for duplicate username and refresh behavior once the session contract is implemented later

### Task 2: Replace address monkeypatch tests with real authenticated persistence tests

**Files:**
- Modify: `tests/api/test_address_routes.py`
- Test: `tests/api/test_address_routes.py`

- [ ] **Step 1: Add an auth helper that uses real register auto-login responses**

In `tests/api/test_address_routes.py`, insert this helper after `client = TestClient(app, raise_server_exceptions=False)`:

```python
def auth_headers(username: str) -> dict[str, str]:
    register_response = client.post(
        "/auth/register",
        json={
            "username": username,
            "password": "strong-password",
            "full_name": f"{username}-name",
            "phone": "13800000009",
        },
    )
    assert register_response.status_code == 201
    access_token = register_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}
```

- [ ] **Step 2: Keep the unauthenticated guard test unchanged**

Leave `test_address_crud_requires_authentication` in place exactly as it is.

- [ ] **Step 3: Replace the monkeypatched CRUD test with a real multiple-address persistence test**

Replace `test_create_update_delete_and_set_default_address` in `tests/api/test_address_routes.py` with this test:

```python
def test_authenticated_user_can_create_and_list_multiple_addresses() -> None:
    headers = auth_headers("address_owner")

    first_response = client.post(
        "/addresses",
        headers=headers,
        json={
            "label": "家",
            "contact_name": "张三",
            "contact_phone": "13800000001",
            "city": "上海",
            "district": "静安",
            "detail_address": "南京西路 100 号",
            "longitude": 121.45,
            "latitude": 31.23,
            "is_default": True,
        },
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/addresses",
        headers=headers,
        json={
            "label": "公司",
            "contact_name": "张三",
            "contact_phone": "13800000001",
            "city": "上海",
            "district": "徐汇",
            "detail_address": "漕溪北路 200 号",
            "longitude": 121.43,
            "latitude": 31.19,
            "is_default": False,
        },
    )
    assert second_response.status_code == 201

    list_response = client.get("/addresses", headers=headers)

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": 1,
            "label": "家",
            "contact_name": "张三",
            "contact_phone": "13800000001",
            "city": "上海",
            "district": "静安",
            "detail_address": "南京西路 100 号",
            "longitude": 121.45,
            "latitude": 31.23,
            "is_default": True,
        },
        {
            "id": 2,
            "label": "公司",
            "contact_name": "张三",
            "contact_phone": "13800000001",
            "city": "上海",
            "district": "徐汇",
            "detail_address": "漕溪北路 200 号",
            "longitude": 121.43,
            "latitude": 31.19,
            "is_default": False,
        },
    ]
```

- [ ] **Step 4: Add a real default-address switching test**

Append this test to `tests/api/test_address_routes.py`:

```python
def test_set_default_address_only_changes_current_users_addresses() -> None:
    headers = auth_headers("default_owner")

    first_id = client.post(
        "/addresses",
        headers=headers,
        json={
            "label": "家",
            "contact_name": "王五",
            "contact_phone": "13800000004",
            "city": "上海",
            "district": "静安",
            "detail_address": "南京西路 300 号",
            "longitude": 121.46,
            "latitude": 31.22,
            "is_default": True,
        },
    ).json()["id"]

    second_id = client.post(
        "/addresses",
        headers=headers,
        json={
            "label": "公司",
            "contact_name": "王五",
            "contact_phone": "13800000004",
            "city": "上海",
            "district": "浦东",
            "detail_address": "张杨路 500 号",
            "longitude": 121.54,
            "latitude": 31.23,
            "is_default": False,
        },
    ).json()["id"]

    default_response = client.post(f"/addresses/{second_id}/default", headers=headers)
    assert default_response.status_code == 200
    assert default_response.json() == {"success": True, "address_id": second_id}

    list_response = client.get("/addresses", headers=headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [second_id, first_id]
    assert [item["is_default"] for item in list_response.json()] == [True, False]
```

- [ ] **Step 5: Add a cross-user isolation test and login bootstrap assertion**

Append this test to `tests/api/test_address_routes.py`:

```python
def test_users_only_see_their_own_addresses_and_login_bootstrap_matches_storage() -> None:
    owner_headers = auth_headers("owner_user")
    other_headers = auth_headers("other_user")

    create_response = client.post(
        "/addresses",
        headers=owner_headers,
        json={
            "label": "家",
            "contact_name": "赵六",
            "contact_phone": "13800000005",
            "city": "上海",
            "district": "杨浦",
            "detail_address": "黄兴路 88 号",
            "longitude": 121.52,
            "latitude": 31.29,
            "is_default": True,
        },
    )
    assert create_response.status_code == 201

    other_list_response = client.get("/addresses", headers=other_headers)
    assert other_list_response.status_code == 200
    assert other_list_response.json() == []

    relogin_response = client.post(
        "/auth/login",
        json={"username": "owner_user", "password": "strong-password"},
    )
    assert relogin_response.status_code == 200
    assert relogin_response.json()["addresses"] == [
        {
            "id": 1,
            "label": "家",
            "contact_name": "赵六",
            "contact_phone": "13800000005",
            "city": "上海",
            "district": "杨浦",
            "detail_address": "黄兴路 88 号",
            "longitude": 121.52,
            "latitude": 31.29,
            "is_default": True,
        }
    ]
```

- [ ] **Step 6: Run the address route tests to verify the bootstrap helper now fails for the right missing register/login session fields**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/api/test_address_routes.py -q
```

Expected:
- PASS for unauthenticated access guard
- FAIL in `auth_headers(...)` because register responses do not yet include `access_token`
- FAIL in relogin bootstrap assertion because login does not yet include `addresses`

### Task 3: Implement the unified auth session response and make the integration tests pass

**Files:**
- Modify: `api/schemas.py`
- Modify: `service/auth_service.py`
- Modify: `api/routes/auth.py`
- Verify: `repository/user_repository.py`
- Verify: `service/user_profile_service.py`
- Test: `tests/api/test_auth_routes.py`
- Test: `tests/api/test_address_routes.py`

- [ ] **Step 1: Add the new auth session schema while preserving refresh compatibility**

In `api/schemas.py`, insert this class immediately after `CurrentUserResponse`:

```python
class AuthSessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    user: CurrentUserResponse
    addresses: list[AddressResponse]
```

Do not remove `TokenPairResponse`; `POST /auth/refresh` still uses it.

- [ ] **Step 2: Teach `AuthService` how to serialize addresses and compose a session response**

In `service/auth_service.py`, update the imports and add session helpers so the file looks like this:

```python
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
```

- [ ] **Step 3: Switch the auth route response models to the new session schema**

In `api/routes/auth.py`, update the imports and route decorators so the top of the file becomes:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.deps import get_current_user
from api.models.user import User
from api.schemas import AuthSessionResponse, CurrentUserResponse, RefreshTokenRequest, RegisterRequest, TokenPairResponse, LoginRequest
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
```

Leave `/auth/refresh` and `/auth/me` unchanged.

- [ ] **Step 4: Run the focused auth and address integration tests**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/api/test_auth_routes.py tests/api/test_address_routes.py -q
```

Expected:
- PASS
- Register persists users and returns session payload
- Login validates stored credentials and returns saved addresses
- Address CRUD remains database-backed and user-scoped

- [ ] **Step 5: Run one more regression check on the authenticated routes together**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/api/test_auth_routes.py tests/api/test_address_routes.py -q
```

Expected:
- PASS again with the same database-backed session/address behavior
- No monkeypatched address service calls remain in the address route tests

## Self-Review Notes

- **Spec coverage:**
  - Register persists users + auto-login → Task 1 and Task 3
  - Login validates stored users + returns token/user/addresses → Task 1 and Task 3
  - Multiple saved addresses including phone/coordinates → Task 2
  - Logged-in users see previously saved addresses → Task 1, Task 2, and Task 3
  - Existing `/addresses` endpoints remain the management surface → Task 2 and Task 3
- **Placeholder scan:** no `TBD`, `TODO`, or “similar to previous task” placeholders remain.
- **Type consistency:** `AuthSessionResponse`, `CurrentUserResponse`, and `AddressResponse` are used consistently in both the plan and the proposed route/service changes.
