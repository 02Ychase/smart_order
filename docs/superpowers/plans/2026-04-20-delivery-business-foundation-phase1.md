# Delivery Business Foundation Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first-phase Meituan-like delivery business foundation for smart_order: authenticated user flow, merchant/dish catalog, cross-merchant cart, address and delivery quote handling, parent/child order checkout with mock payment, seed data, and agent-context-ready APIs.

**Architecture:** Keep FastAPI as the backend entrypoint and Vue + Element Plus as the frontend shell, but replace the current single-purpose demo flow with modular business domains. Introduce persistent relational data models for users, addresses, merchants, dishes, cart, and orders; expose domain APIs through dedicated route modules; seed realistic merchant/dish/location data; and reshape the frontend into a user-side delivery app with catalog, checkout, and orders. Reserve a dedicated agent-context API boundary now so later RAG and assistant work can consume structured business state instead of scraping product endpoints.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, Alembic, MySQL connector, pytest, Vue 3, Vite, Element Plus, Axios

---

## File Structure

- Modify: `requirements.txt` — add backend persistence, migration, auth, and test dependencies.
- Modify: `pyproject.toml` — mirror runtime/test dependencies for local installs.
- Modify: `README.md` — replace the current minimal run notes with setup, seed, backend, and frontend instructions.
- Modify: `run.py` — point local boot at the modular FastAPI app.
- Replace: `api/main.py` — turn the current monolithic API into a pure app assembly entrypoint.
- Create: `api/db.py` — SQLAlchemy engine, session factory, and session dependency.
- Create: `api/models/__init__.py` — export ORM models.
- Create: `api/models/user.py` — `User` and `UserAddress` ORM models.
- Create: `api/models/catalog.py` — `Merchant`, `DishCategory`, and `Dish` ORM models.
- Create: `api/models/cart.py` — `Cart` and `CartItem` ORM models.
- Create: `api/models/order.py` — `CheckoutOrder`, `MerchantOrder`, `OrderItem`, `PaymentRecord`, and `DeliveryQuote` ORM models.
- Create: `api/schemas.py` — request/response DTOs for auth, catalog, cart, addresses, orders, and health.
- Create: `api/deps.py` — shared auth/session dependencies.
- Create: `api/security.py` — password hashing, JWT issue/verify helpers, refresh-token helpers.
- Create: `api/routes/__init__.py` — route exports.
- Create: `api/routes/auth.py` — registration, login, token refresh, current-user endpoints.
- Create: `api/routes/catalog.py` — merchant list/detail and dish list endpoints.
- Create: `api/routes/address.py` — address CRUD endpoints.
- Create: `api/routes/cart.py` — cart read/write endpoints.
- Create: `api/routes/orders.py` — checkout preview, submit, pay, order list/detail endpoints.
- Create: `api/routes/agent_context.py` — structured business context endpoints reserved for future assistant use.
- Create: `api/routes/health.py` — health endpoint.
- Create: `service/catalog_service.py` — merchant/dish query logic.
- Create: `service/user_profile_service.py` — user/address management logic.
- Create: `service/cart_service.py` — cart aggregation and mutation logic.
- Create: `service/order_service.py` — checkout validation, split-order creation, payment simulation, status helpers.
- Create: `service/auth_service.py` — registration and login orchestration.
- Create: `repository/catalog_repository.py` — merchant/dish data access helpers.
- Create: `repository/user_repository.py` — user/address data access helpers.
- Create: `repository/cart_repository.py` — cart data access helpers.
- Create: `repository/order_repository.py` — order and payment data access helpers.
- Create: `database/migrations/...` — Alembic migration scripts for all new tables.
- Create: `database/seeds/merchant_seed_data.py` — merchant, category, and dish seed payloads.
- Create: `tools/seed_demo_data.py` — seed runner that inserts realistic merchants/dishes/addresses.
- Create: `tools/seed_catalog_data.py` — optional catalog-only seed runner.
- Create: `.env.example` — document required environment variables.
- Create: `alembic.ini` — Alembic configuration.
- Create: `tests/conftest.py` — shared test DB/session/app fixtures.
- Create: `tests/api/test_auth_routes.py` — auth API regression tests.
- Create: `tests/api/test_catalog_routes.py` — merchant/dish catalog tests.
- Create: `tests/api/test_address_routes.py` — address CRUD tests.
- Create: `tests/api/test_cart_routes.py` — cross-merchant cart tests.
- Create: `tests/api/test_order_routes.py` — checkout, split-order, payment, order list/detail tests.
- Create: `tests/api/test_agent_context_routes.py` — future-assistant context contract tests.
- Create: `tests/api/test_app_wiring.py` — app route wiring verification.
- Create: `ui/src/api/auth.js` — auth API client helpers.
- Create: `ui/src/api/catalog.js` — merchant/dish API client helpers.
- Create: `ui/src/api/address.js` — address API client helpers.
- Create: `ui/src/api/cart.js` — cart API client helpers.
- Create: `ui/src/api/orders.js` — order API client helpers.
- Modify: `ui/src/api/index.js` — keep shared Axios instance only, remove old demo-specific API wrappers.
- Create: `ui/src/composables/useAuth.js` — token and current-user state.
- Create: `ui/src/composables/useCart.js` — cart state and grouped cart totals.
- Create: `ui/src/utils/currency.js` — currency formatting helper.
- Create: `ui/src/utils/orderStatus.js` — order status label helper.
- Create: `ui/src/views/LoginView.vue` — register/login page.
- Create: `ui/src/views/MerchantListView.vue` — homepage merchant list.
- Create: `ui/src/views/MerchantDetailView.vue` — merchant detail and dish browsing.
- Create: `ui/src/views/CheckoutView.vue` — grouped cart + address select + order preview.
- Create: `ui/src/views/AddressView.vue` — address management.
- Create: `ui/src/views/OrderListView.vue` — parent order list with child-order summaries.
- Create: `ui/src/views/OrderDetailView.vue` — parent/child order detail.
- Modify: `ui/src/App.vue` — replace current chat/delivery/menu demo layout with delivery-platform shell and assistant placeholder.

---

### Task 1: Add backend, migration, and test dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write the failing dependency metadata test**

Create `tests/test_project_dependencies.py` with this content:

```python
from pathlib import Path


REQUIRED_REQUIREMENTS = {
    "sqlalchemy>=2.0.36",
    "alembic>=1.14.0",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "pytest>=8.2.0",
    "httpx>=0.27.0",
}


REQUIRED_PYPROJECT = {
    "SQLAlchemy>=2.0.36",
    "alembic>=1.14.0",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "pytest>=8.2.0",
    "httpx>=0.27.0",
}


def test_requirements_contains_phase1_dependencies() -> None:
    contents = Path("requirements.txt").read_text(encoding="utf-8")

    for requirement in REQUIRED_REQUIREMENTS:
        assert requirement in contents



def test_pyproject_contains_phase1_dependencies() -> None:
    contents = Path("pyproject.toml").read_text(encoding="utf-8")

    for requirement in REQUIRED_PYPROJECT:
        assert requirement in contents
```

- [ ] **Step 2: Run the dependency metadata test to verify it fails**

Run:

```bash
python -m pytest tests/test_project_dependencies.py -v
```

Expected: FAIL because `requirements.txt` and `pyproject.toml` do not yet include the listed dependencies.

- [ ] **Step 3: Update `requirements.txt` with the missing packages**

Append these lines to `requirements.txt` after the current database/tooling section:

```txt
SQLAlchemy>=2.0.36
alembic>=1.14.0
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0
pytest>=8.2.0
httpx>=0.27.0
```

- [ ] **Step 4: Update `pyproject.toml` to mirror the runtime and test dependencies**

Replace the empty dependency list with this block:

```toml
dependencies = [
    "langchain>=1.0.7",
    "langchain-openai>=1.0.3",
    "langchain-community>=0.4.1",
    "langchain-core>=1.0.7",
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "mysql-connector-python~=9.4.0",
    "SQLAlchemy>=2.0.36",
    "alembic>=1.14.0",
    "pinecone~=7.3.0",
    "dashscope>=1.14.0",
    "python-dotenv>=1.0.0",
    "requests>=2.31.0",
    "pydantic~=2.11.7",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "pytest>=8.2.0",
    "httpx>=0.27.0",
]
```

- [ ] **Step 5: Re-run the dependency metadata test**

Run:

```bash
python -m pytest tests/test_project_dependencies.py -v
```

Expected:

```txt
tests/test_project_dependencies.py::test_requirements_contains_phase1_dependencies PASSED
tests/test_project_dependencies.py::test_pyproject_contains_phase1_dependencies PASSED
```

- [ ] **Step 6: Commit the dependency task**

Run:

```bash
git add requirements.txt pyproject.toml tests/test_project_dependencies.py
git commit -m "build: add phase one backend dependencies"
```

### Task 2: Introduce database bootstrap and core ORM models

**Files:**
- Create: `api/db.py`
- Create: `api/models/__init__.py`
- Create: `api/models/user.py`
- Create: `api/models/catalog.py`
- Create: `api/models/cart.py`
- Create: `api/models/order.py`
- Test: `tests/test_models_metadata.py`

- [ ] **Step 1: Write the failing ORM metadata test**

Create `tests/test_models_metadata.py` with this content:

```python
from api.models import Base


EXPECTED_TABLES = {
    "users",
    "user_addresses",
    "merchants",
    "dish_categories",
    "dishes",
    "carts",
    "cart_items",
    "checkout_orders",
    "merchant_orders",
    "order_items",
    "payment_records",
    "delivery_quotes",
}



def test_phase1_models_register_expected_tables() -> None:
    assert EXPECTED_TABLES == set(Base.metadata.tables)
```

- [ ] **Step 2: Run the ORM metadata test to verify it fails**

Run:

```bash
python -m pytest tests/test_models_metadata.py -v
```

Expected: FAIL because `api.models` and the referenced tables do not exist yet.

- [ ] **Step 3: Create `api/db.py` with SQLAlchemy bootstrap**

Create `api/db.py` with this content:

```python
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+mysqlconnector://root:password@localhost:3306/smart_order",
)


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)



def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Step 4: Create the user and catalog ORM models**

Create `api/models/user.py` with this content:

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(128), default="")
    phone: Mapped[str] = mapped_column(String(32), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    addresses: Mapped[list["UserAddress"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserAddress(Base):
    __tablename__ = "user_addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    label: Mapped[str] = mapped_column(String(32))
    contact_name: Mapped[str] = mapped_column(String(64))
    contact_phone: Mapped[str] = mapped_column(String(32))
    city: Mapped[str] = mapped_column(String(64))
    district: Mapped[str] = mapped_column(String(64))
    detail_address: Mapped[str] = mapped_column(Text)
    longitude: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="addresses")
```

Create `api/models/catalog.py` with this content:

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(64))
    district: Mapped[str] = mapped_column(String(64))
    address: Mapped[str] = mapped_column(Text)
    longitude: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    delivery_radius_meters: Mapped[int] = mapped_column(Integer, default=3000)
    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    min_order_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    avg_delivery_minutes: Mapped[int] = mapped_column(Integer, default=30)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=4.5)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    categories: Mapped[list["DishCategory"]] = relationship(back_populates="merchant", cascade="all, delete-orphan")
    dishes: Mapped[list["Dish"]] = relationship(back_populates="merchant", cascade="all, delete-orphan")


class DishCategory(Base):
    __tablename__ = "dish_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    merchant: Mapped[Merchant] = relationship(back_populates="categories")
    dishes: Mapped[list["Dish"]] = relationship(back_populates="category")


class Dish(Base):
    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("dish_categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    image_url: Mapped[str] = mapped_column(String(255), default="")
    tags: Mapped[str] = mapped_column(String(255), default="")
    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    merchant: Mapped[Merchant] = relationship(back_populates="dishes")
    category: Mapped[DishCategory] = relationship(back_populates="dishes")
```

- [ ] **Step 5: Create cart, order, and model export modules**

Create `api/models/cart.py` with this content:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_snapshot: Mapped[float] = mapped_column(Numeric(10, 2))
```

Create `api/models/order.py` with this content:

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class CheckoutOrder(Base):
    __tablename__ = "checkout_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    address_snapshot: Mapped[str] = mapped_column(Text)
    goods_amount: Mapped[float] = mapped_column(Numeric(10, 2))
    delivery_amount: Mapped[float] = mapped_column(Numeric(10, 2))
    payable_amount: Mapped[float] = mapped_column(Numeric(10, 2))
    payment_status: Mapped[str] = mapped_column(String(32), default="pending_payment")
    order_status: Mapped[str] = mapped_column(String(32), default="pending_payment")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MerchantOrder(Base):
    __tablename__ = "merchant_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkout_order_id: Mapped[int] = mapped_column(ForeignKey("checkout_orders.id"), index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    goods_amount: Mapped[float] = mapped_column(Numeric(10, 2))
    delivery_amount: Mapped[float] = mapped_column(Numeric(10, 2))
    payable_amount: Mapped[float] = mapped_column(Numeric(10, 2))
    order_status: Mapped[str] = mapped_column(String(32), default="pending_payment")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_order_id: Mapped[int] = mapped_column(ForeignKey("merchant_orders.id"), index=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id"), index=True)
    dish_name_snapshot: Mapped[str] = mapped_column(String(128))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_snapshot: Mapped[float] = mapped_column(Numeric(10, 2))


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkout_order_id: Mapped[int] = mapped_column(ForeignKey("checkout_orders.id"), index=True)
    channel: Mapped[str] = mapped_column(String(32), default="mock")
    request_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    payment_status: Mapped[str] = mapped_column(String(32), default="succeeded")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DeliveryQuote(Base):
    __tablename__ = "delivery_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkout_order_id: Mapped[int] = mapped_column(ForeignKey("checkout_orders.id"), index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    in_range: Mapped[bool] = mapped_column(Boolean, default=True)
    distance_meters: Mapped[int] = mapped_column(Integer, default=0)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=0)
    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    message: Mapped[str] = mapped_column(Text, default="")
```

Create `api/models/__init__.py` with this content:

```python
from api.db import Base
from api.models.cart import Cart, CartItem
from api.models.catalog import Dish, DishCategory, Merchant
from api.models.order import CheckoutOrder, DeliveryQuote, MerchantOrder, OrderItem, PaymentRecord
from api.models.user import User, UserAddress

__all__ = [
    "Base",
    "User",
    "UserAddress",
    "Merchant",
    "DishCategory",
    "Dish",
    "Cart",
    "CartItem",
    "CheckoutOrder",
    "MerchantOrder",
    "OrderItem",
    "PaymentRecord",
    "DeliveryQuote",
]
```

- [ ] **Step 6: Re-run the ORM metadata test**

Run:

```bash
python -m pytest tests/test_models_metadata.py -v
```

Expected:

```txt
tests/test_models_metadata.py::test_phase1_models_register_expected_tables PASSED
```

- [ ] **Step 7: Commit the model task**

Run:

```bash
git add api/db.py api/models tests/test_models_metadata.py
git commit -m "feat: add phase one order domain models"
```

### Task 3: Add schema, security, and auth domain wiring

**Files:**
- Create: `api/schemas.py`
- Create: `api/security.py`
- Create: `api/deps.py`
- Create: `repository/user_repository.py`
- Create: `service/auth_service.py`
- Create: `api/routes/auth.py`
- Test: `tests/api/test_auth_routes.py`

- [ ] **Step 1: Write the failing auth route tests**

Create `tests/api/test_auth_routes.py` with this content:

```python
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app, raise_server_exceptions=False)



def test_register_login_refresh_and_current_user_round_trip() -> None:
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
    assert register_response.json()["username"] == "phase1_user"

    login_response = client.post(
        "/auth/login",
        json={"username": "phase1_user", "password": "strong-password"},
    )

    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["access_token"]
    assert login_payload["refresh_token"]
    assert login_payload["token_type"] == "bearer"

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {login_payload['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["username"] == "phase1_user"

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": login_payload["refresh_token"]},
    )

    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()
    assert refresh_payload["access_token"]
    assert refresh_payload["refresh_token"]
```

- [ ] **Step 2: Run the auth route test to verify it fails**

Run:

```bash
python -m pytest tests/api/test_auth_routes.py -v
```

Expected: FAIL because `/auth/register`, `/auth/login`, `/auth/me`, and `/auth/refresh` do not exist yet.

- [ ] **Step 3: Create the auth DTOs and security helpers**

Create `api/schemas.py` with this content:

```python
from typing import Literal

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = ""
    phone: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class CurrentUserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    phone: str


class AddressRequest(BaseModel):
    label: str
    contact_name: str
    contact_phone: str
    city: str
    district: str
    detail_address: str
    longitude: float
    latitude: float
    is_default: bool = False


class AddressResponse(AddressRequest):
    id: int


class MerchantSummaryResponse(BaseModel):
    id: int
    name: str
    description: str
    district: str
    delivery_fee: float
    min_order_amount: float
    avg_delivery_minutes: int
    rating: float


class DishResponse(BaseModel):
    id: int
    merchant_id: int
    category_id: int
    name: str
    description: str
    price: float
    tags: list[str]
    is_recommended: bool


class CartMutationRequest(BaseModel):
    dish_id: int
    quantity: int = Field(ge=1)


class CheckoutPreviewRequest(BaseModel):
    address_id: int


class MockPayRequest(BaseModel):
    checkout_order_id: int


class HealthResponse(BaseModel):
    status: str
    service: str
```

Create `api/security.py` with this content:

```python
from datetime import datetime, timedelta, timezone
import os

from jose import JWTError, jwt
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "smart-order-phase1-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30
REFRESH_TOKEN_DAYS = 7



def hash_password(password: str) -> str:
    return pwd_context.hash(password)



def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)



def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    expires_at = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": subject, "type": token_type, "exp": expires_at}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)



def create_access_token(subject: str) -> str:
    return _create_token(subject, timedelta(minutes=ACCESS_TOKEN_MINUTES), "access")



def create_refresh_token(subject: str) -> str:
    return _create_token(subject, timedelta(days=REFRESH_TOKEN_DAYS), "refresh")



def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
```

- [ ] **Step 4: Create the repository/service/auth route implementation**

Create `repository/user_repository.py` with this content:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.user import User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username))

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def create_user(self, username: str, password_hash: str, full_name: str, phone: str) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            phone=phone,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
```

Create `service/auth_service.py` with this content:

```python
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from api.schemas import CurrentUserResponse, TokenPairResponse
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

    def register(self, username: str, password: str, full_name: str, phone: str) -> CurrentUserResponse:
        if self.users.get_by_username(username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username already exists")

        user = self.users.create_user(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            phone=phone,
        )
        return self._serialize_user(user)

    def login(self, username: str, password: str) -> TokenPairResponse:
        user = self.users.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

        return TokenPairResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )

    def refresh(self, refresh_token: str) -> TokenPairResponse:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token")

        user = self.users.get_by_id(int(payload["sub"]))
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

Create `api/routes/auth.py` with this content:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.deps import get_current_user
from api.models.user import User
from api.schemas import CurrentUserResponse, LoginRequest, RefreshTokenRequest, RegisterRequest, TokenPairResponse
from service.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=CurrentUserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, session: Session = Depends(get_db_session)) -> CurrentUserResponse:
    return AuthService(session).register(
        username=request.username,
        password=request.password,
        full_name=request.full_name,
        phone=request.phone,
    )


@router.post("/login", response_model=TokenPairResponse)
def login(request: LoginRequest, session: Session = Depends(get_db_session)) -> TokenPairResponse:
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
```

Create `api/deps.py` with this content:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.models.user import User
from api.security import decode_token


bearer_scheme = HTTPBearer(auto_error=False)



def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_db_session),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")

    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise ValueError("invalid token type")
        user_id = int(payload["sub"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user
```

- [ ] **Step 5: Re-run the auth route test**

Run:

```bash
python -m pytest tests/api/test_auth_routes.py -v
```

Expected:

```txt
tests/api/test_auth_routes.py::test_register_login_refresh_and_current_user_round_trip PASSED
```

- [ ] **Step 6: Commit the auth task**

Run:

```bash
git add api/schemas.py api/security.py api/deps.py api/routes/auth.py repository/user_repository.py service/auth_service.py tests/api/test_auth_routes.py
git commit -m "feat: add auth foundation routes"
```

### Task 4: Assemble the modular FastAPI app and health route

**Files:**
- Replace: `api/main.py`
- Create: `api/routes/__init__.py`
- Create: `api/routes/health.py`
- Test: `tests/api/test_app_wiring.py`

- [ ] **Step 1: Write the failing app wiring test**

Create `tests/api/test_app_wiring.py` with this content:

```python
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app, raise_server_exceptions=False)



def test_health_endpoint_returns_expected_payload() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "smart-order api"}



def test_openapi_contains_phase1_domain_routes() -> None:
    paths = app.openapi()["paths"]

    assert "/auth/register" in paths
    assert "/auth/login" in paths
    assert "/health" in paths
```

- [ ] **Step 2: Run the app wiring test to verify it fails**

Run:

```bash
python -m pytest tests/api/test_app_wiring.py -v
```

Expected: FAIL because the current `api/main.py` only exposes the old demo routes.

- [ ] **Step 3: Create the route export and health route modules**

Create `api/routes/health.py` with this content:

```python
from fastapi import APIRouter

from api.schemas import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="healthy", service="smart-order api")
```

Create `api/routes/__init__.py` with this content:

```python
from api.routes.auth import router as auth_router
from api.routes.health import router as health_router

__all__ = ["auth_router", "health_router"]
```

- [ ] **Step 4: Replace `api/main.py` with a pure app-assembly entrypoint**

Replace `api/main.py` with this content:

```python
from fastapi import FastAPI

from api.routes import auth_router, health_router


app = FastAPI(
    title="smart-order api",
    description="Phase one delivery business foundation APIs",
)

app.include_router(auth_router)
app.include_router(health_router)
```

- [ ] **Step 5: Re-run the app wiring test**

Run:

```bash
python -m pytest tests/api/test_app_wiring.py -v
```

Expected:

```txt
tests/api/test_app_wiring.py::test_health_endpoint_returns_expected_payload PASSED
tests/api/test_app_wiring.py::test_openapi_contains_phase1_domain_routes PASSED
```

- [ ] **Step 6: Commit the app assembly task**

Run:

```bash
git add api/main.py api/routes/__init__.py api/routes/health.py tests/api/test_app_wiring.py
git commit -m "refactor: assemble modular fastapi app"
```

### Task 5: Add merchant and dish catalog APIs

**Files:**
- Create: `repository/catalog_repository.py`
- Create: `service/catalog_service.py`
- Create: `api/routes/catalog.py`
- Modify: `api/routes/__init__.py`
- Test: `tests/api/test_catalog_routes.py`

- [ ] **Step 1: Write the failing catalog route tests**

Create `tests/api/test_catalog_routes.py` with this content:

```python
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app, raise_server_exceptions=False)



def test_list_merchants_returns_summary_items(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routes.catalog.CatalogService.list_merchants",
        lambda self, district=None: [
            {
                "id": 1,
                "name": "川湘小馆",
                "description": "下饭川菜",
                "district": "静安",
                "delivery_fee": 4.0,
                "min_order_amount": 20.0,
                "avg_delivery_minutes": 28,
                "rating": 4.7,
            }
        ],
    )

    response = client.get("/catalog/merchants")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "川湘小馆"



def test_list_dishes_returns_recommended_and_tag_lists(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routes.catalog.CatalogService.list_dishes_by_merchant",
        lambda self, merchant_id: [
            {
                "id": 11,
                "merchant_id": merchant_id,
                "category_id": 2,
                "name": "鱼香肉丝",
                "description": "招牌热菜",
                "price": 28.0,
                "tags": ["招牌", "下饭"],
                "is_recommended": True,
            }
        ],
    )

    response = client.get("/catalog/merchants/1/dishes")

    assert response.status_code == 200
    assert response.json()[0]["tags"] == ["招牌", "下饭"]
```

- [ ] **Step 2: Run the catalog route tests to verify they fail**

Run:

```bash
python -m pytest tests/api/test_catalog_routes.py -v
```

Expected: FAIL because the catalog routes do not exist yet.

- [ ] **Step 3: Create the repository and service layers for catalog reads**

Create `repository/catalog_repository.py` with this content:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.catalog import Dish, Merchant


class CatalogRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_merchants(self, district: str | None = None) -> list[Merchant]:
        statement = select(Merchant).where(Merchant.is_open.is_(True)).order_by(Merchant.rating.desc(), Merchant.id.asc())
        if district:
            statement = statement.where(Merchant.district == district)
        return list(self.session.scalars(statement))

    def list_dishes_by_merchant(self, merchant_id: int) -> list[Dish]:
        statement = select(Dish).where(Dish.merchant_id == merchant_id, Dish.is_available.is_(True)).order_by(Dish.is_recommended.desc(), Dish.id.asc())
        return list(self.session.scalars(statement))
```

Create `service/catalog_service.py` with this content:

```python
from sqlalchemy.orm import Session

from repository.catalog_repository import CatalogRepository


class CatalogService:
    def __init__(self, session: Session):
        self.catalog = CatalogRepository(session)

    def list_merchants(self, district: str | None = None) -> list[dict]:
        merchants = self.catalog.list_merchants(district=district)
        return [
            {
                "id": merchant.id,
                "name": merchant.name,
                "description": merchant.description,
                "district": merchant.district,
                "delivery_fee": float(merchant.delivery_fee),
                "min_order_amount": float(merchant.min_order_amount),
                "avg_delivery_minutes": merchant.avg_delivery_minutes,
                "rating": float(merchant.rating),
            }
            for merchant in merchants
        ]

    def list_dishes_by_merchant(self, merchant_id: int) -> list[dict]:
        dishes = self.catalog.list_dishes_by_merchant(merchant_id)
        return [
            {
                "id": dish.id,
                "merchant_id": dish.merchant_id,
                "category_id": dish.category_id,
                "name": dish.name,
                "description": dish.description,
                "price": float(dish.price),
                "tags": [tag for tag in dish.tags.split(",") if tag],
                "is_recommended": dish.is_recommended,
            }
            for dish in dishes
        ]
```

- [ ] **Step 4: Create the catalog route module and register it**

Create `api/routes/catalog.py` with this content:

```python
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
def list_dishes_by_merchant(merchant_id: int, session: Session = Depends(get_db_session)) -> list[DishResponse]:
    return CatalogService(session).list_dishes_by_merchant(merchant_id)
```

Update `api/routes/__init__.py` to this content:

```python
from api.routes.auth import router as auth_router
from api.routes.catalog import router as catalog_router
from api.routes.health import router as health_router

__all__ = ["auth_router", "catalog_router", "health_router"]
```

Update `api/main.py` include list to this block:

```python
from api.routes import auth_router, catalog_router, health_router

app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(health_router)
```

- [ ] **Step 5: Re-run the catalog route tests**

Run:

```bash
python -m pytest tests/api/test_catalog_routes.py -v
```

Expected:

```txt
tests/api/test_catalog_routes.py::test_list_merchants_returns_summary_items PASSED
tests/api/test_catalog_routes.py::test_list_dishes_returns_recommended_and_tag_lists PASSED
```

- [ ] **Step 6: Commit the catalog task**

Run:

```bash
git add repository/catalog_repository.py service/catalog_service.py api/routes/catalog.py api/routes/__init__.py api/main.py tests/api/test_catalog_routes.py
git commit -m "feat: add merchant catalog routes"
```

### Task 6: Add full address CRUD endpoints behind authentication

**Files:**
- Modify: `api/schemas.py`
- Create: `service/user_profile_service.py`
- Modify: `repository/user_repository.py`
- Create: `api/routes/address.py`
- Modify: `api/routes/__init__.py`
- Modify: `api/main.py`
- Test: `tests/api/test_address_routes.py`

- [ ] **Step 1: Write the failing address route tests**

Create `tests/api/test_address_routes.py` with this content:

```python
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app, raise_server_exceptions=False)



def test_address_crud_requires_authentication() -> None:
    response = client.get("/addresses")

    assert response.status_code == 401



def test_create_update_delete_and_set_default_address(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routes.address.UserProfileService.create_address",
        lambda self, user_id, payload: {
            "id": 1,
            "label": payload.label,
            "contact_name": payload.contact_name,
            "contact_phone": payload.contact_phone,
            "city": payload.city,
            "district": payload.district,
            "detail_address": payload.detail_address,
            "longitude": payload.longitude,
            "latitude": payload.latitude,
            "is_default": payload.is_default,
        },
    )
    monkeypatch.setattr(
        "api.routes.address.UserProfileService.update_address",
        lambda self, user_id, address_id, payload: {
            "id": address_id,
            "label": payload.label,
            "contact_name": payload.contact_name,
            "contact_phone": payload.contact_phone,
            "city": payload.city,
            "district": payload.district,
            "detail_address": payload.detail_address,
            "longitude": payload.longitude,
            "latitude": payload.latitude,
            "is_default": payload.is_default,
        },
    )
    monkeypatch.setattr(
        "api.routes.address.UserProfileService.set_default_address",
        lambda self, user_id, address_id: {"success": True, "address_id": address_id},
    )
    monkeypatch.setattr(
        "api.routes.address.UserProfileService.delete_address",
        lambda self, user_id, address_id: {"success": True, "address_id": address_id},
    )
    monkeypatch.setattr("api.routes.address.get_current_user", lambda: type("User", (), {"id": 7})())

    create_response = client.post(
        "/addresses",
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
    assert create_response.status_code == 201
    assert create_response.json()["label"] == "家"

    update_response = client.put(
        "/addresses/1",
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
    assert update_response.status_code == 200
    assert update_response.json()["label"] == "公司"

    default_response = client.post("/addresses/1/default")
    assert default_response.status_code == 200
    assert default_response.json() == {"success": True, "address_id": 1}

    delete_response = client.delete("/addresses/1")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"success": True, "address_id": 1}
```

- [ ] **Step 2: Run the address route tests to verify they fail**

Run:

```bash
python -m pytest tests/api/test_address_routes.py -v
```

Expected: FAIL because `/addresses`, `/addresses/{address_id}`, and `/addresses/{address_id}/default` do not exist yet.

- [ ] **Step 3: Extend the user repository and create the profile service**

Append these methods to `repository/user_repository.py` inside `UserRepository`:

```python
    def list_addresses(self, user_id: int):
        from sqlalchemy import select
        from api.models.user import UserAddress

        statement = select(UserAddress).where(UserAddress.user_id == user_id).order_by(UserAddress.is_default.desc(), UserAddress.id.asc())
        return list(self.session.scalars(statement))

    def get_address(self, user_id: int, address_id: int):
        from sqlalchemy import select
        from api.models.user import UserAddress

        statement = select(UserAddress).where(UserAddress.user_id == user_id, UserAddress.id == address_id)
        return self.session.scalar(statement)

    def create_address(self, user_id: int, payload):
        from api.models.user import UserAddress

        if payload.is_default:
            for address in self.list_addresses(user_id):
                address.is_default = False

        address = UserAddress(user_id=user_id, **payload.model_dump())
        self.session.add(address)
        self.session.commit()
        self.session.refresh(address)
        return address

    def update_address(self, user_id: int, address_id: int, payload):
        address = self.get_address(user_id, address_id)
        if address is None:
            return None

        if payload.is_default:
            for candidate in self.list_addresses(user_id):
                candidate.is_default = candidate.id == address_id

        for field, value in payload.model_dump().items():
            setattr(address, field, value)

        self.session.commit()
        self.session.refresh(address)
        return address

    def set_default_address(self, user_id: int, address_id: int):
        address = self.get_address(user_id, address_id)
        if address is None:
            return None

        for candidate in self.list_addresses(user_id):
            candidate.is_default = candidate.id == address_id

        self.session.commit()
        self.session.refresh(address)
        return address

    def delete_address(self, user_id: int, address_id: int) -> bool:
        address = self.get_address(user_id, address_id)
        if address is None:
            return False

        self.session.delete(address)
        self.session.commit()
        return True
```

Create `service/user_profile_service.py` with this content:

```python
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repository.user_repository import UserRepository


class UserProfileService:
    def __init__(self, session: Session):
        self.users = UserRepository(session)

    def _serialize_address(self, address) -> dict:
        return {
            "id": address.id,
            "label": address.label,
            "contact_name": address.contact_name,
            "contact_phone": address.contact_phone,
            "city": address.city,
            "district": address.district,
            "detail_address": address.detail_address,
            "longitude": address.longitude,
            "latitude": address.latitude,
            "is_default": address.is_default,
        }

    def list_addresses(self, user_id: int) -> list[dict]:
        return [self._serialize_address(address) for address in self.users.list_addresses(user_id)]

    def create_address(self, user_id: int, payload) -> dict:
        return self._serialize_address(self.users.create_address(user_id, payload))

    def update_address(self, user_id: int, address_id: int, payload) -> dict:
        address = self.users.update_address(user_id, address_id, payload)
        if address is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="address not found")
        return self._serialize_address(address)

    def set_default_address(self, user_id: int, address_id: int) -> dict:
        address = self.users.set_default_address(user_id, address_id)
        if address is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="address not found")
        return {"success": True, "address_id": address.id}

    def delete_address(self, user_id: int, address_id: int) -> dict:
        deleted = self.users.delete_address(user_id, address_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="address not found")
        return {"success": True, "address_id": address_id}
```

- [ ] **Step 4: Create the address route module and register it**

Create `api/routes/address.py` with this content:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.deps import get_current_user
from api.models.user import User
from api.schemas import AddressRequest, AddressResponse
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


@router.post("/{address_id}/default")
def set_default_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return UserProfileService(session).set_default_address(current_user.id, address_id)


@router.delete("/{address_id}")
def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return UserProfileService(session).delete_address(current_user.id, address_id)
```

Update `api/routes/__init__.py` to this content:

```python
from api.routes.address import router as address_router
from api.routes.auth import router as auth_router
from api.routes.catalog import router as catalog_router
from api.routes.health import router as health_router

__all__ = ["address_router", "auth_router", "catalog_router", "health_router"]
```

Update `api/main.py` includes to this block:

```python
from api.routes import address_router, auth_router, catalog_router, health_router

app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(address_router)
app.include_router(health_router)
```

- [ ] **Step 5: Re-run the address route tests**

Run:

```bash
python -m pytest tests/api/test_address_routes.py -v
```

Expected:

```txt
tests/api/test_address_routes.py::test_address_crud_requires_authentication PASSED
tests/api/test_address_routes.py::test_create_update_delete_and_set_default_address PASSED
```

- [ ] **Step 6: Commit the address task**

Run:

```bash
git add repository/user_repository.py service/user_profile_service.py api/routes/address.py api/routes/__init__.py api/main.py tests/api/test_address_routes.py
git commit -m "feat: add address management routes"
```

### Task 7: Add cross-merchant cart APIs

**Files:**
- Create: `repository/cart_repository.py`
- Create: `service/cart_service.py`
- Create: `api/routes/cart.py`
- Modify: `api/routes/__init__.py`
- Modify: `api/main.py`
- Test: `tests/api/test_cart_routes.py`

- [ ] **Step 1: Write the failing cart route tests**

Create `tests/api/test_cart_routes.py` with this content:

```python
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app, raise_server_exceptions=False)



def test_get_cart_returns_grouped_merchants(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routes.cart.CartService.get_grouped_cart",
        lambda self, user_id: {
            "items": [
                {
                    "merchant_id": 1,
                    "merchant_name": "川湘小馆",
                    "items": [{"dish_id": 11, "dish_name": "鱼香肉丝", "quantity": 2, "unit_price": 28.0}],
                    "subtotal": 56.0,
                }
            ],
            "goods_amount": 56.0,
        },
    )
    monkeypatch.setattr(
        "api.routes.cart.CartService.add_item",
        lambda self, user_id, payload: {"success": True, "dish_id": payload.dish_id, "quantity": payload.quantity},
    )
    monkeypatch.setattr(
        "api.routes.cart.CartService.remove_item",
        lambda self, user_id, dish_id: {"success": True, "dish_id": dish_id},
    )
    monkeypatch.setattr("api.routes.cart.get_current_user", lambda: type("User", (), {"id": 9})())

    get_response = client.get("/cart")
    assert get_response.status_code == 200
    assert get_response.json()["items"][0]["merchant_name"] == "川湘小馆"

    add_response = client.post("/cart/items", json={"dish_id": 11, "quantity": 2})
    assert add_response.status_code == 200
    assert add_response.json() == {"success": True, "dish_id": 11, "quantity": 2}

    remove_response = client.delete("/cart/items/11")
    assert remove_response.status_code == 200
    assert remove_response.json() == {"success": True, "dish_id": 11}
```

- [ ] **Step 2: Run the cart route test to verify it fails**

Run:

```bash
python -m pytest tests/api/test_cart_routes.py -v
```

Expected: FAIL because `/cart`, `/cart/items`, and `/cart/items/{dish_id}` do not exist yet.

- [ ] **Step 3: Create the cart repository and service**

Create `repository/cart_repository.py` with this content:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.cart import Cart, CartItem
from api.models.catalog import Dish, Merchant


class CartRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create_cart(self, user_id: int) -> Cart:
        cart = self.session.scalar(select(Cart).where(Cart.user_id == user_id))
        if cart is None:
            cart = Cart(user_id=user_id)
            self.session.add(cart)
            self.session.commit()
            self.session.refresh(cart)
        return cart

    def list_items(self, user_id: int) -> list[CartItem]:
        cart = self.get_or_create_cart(user_id)
        statement = select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.merchant_id.asc(), CartItem.id.asc())
        return list(self.session.scalars(statement))

    def get_dish(self, dish_id: int) -> Dish | None:
        return self.session.get(Dish, dish_id)

    def get_merchant(self, merchant_id: int) -> Merchant | None:
        return self.session.get(Merchant, merchant_id)

    def upsert_item(self, user_id: int, dish_id: int, quantity: int) -> CartItem:
        cart = self.get_or_create_cart(user_id)
        statement = select(CartItem).where(CartItem.cart_id == cart.id, CartItem.dish_id == dish_id)
        item = self.session.scalar(statement)
        dish = self.get_dish(dish_id)
        if dish is None:
            raise ValueError("dish not found")

        if item is None:
            item = CartItem(
                cart_id=cart.id,
                user_id=user_id,
                merchant_id=dish.merchant_id,
                dish_id=dish.id,
                quantity=quantity,
                unit_price_snapshot=dish.price,
            )
            self.session.add(item)
        else:
            item.quantity = quantity
            item.unit_price_snapshot = dish.price

        self.session.commit()
        self.session.refresh(item)
        return item

    def remove_item(self, user_id: int, dish_id: int) -> bool:
        cart = self.get_or_create_cart(user_id)
        statement = select(CartItem).where(CartItem.cart_id == cart.id, CartItem.dish_id == dish_id)
        item = self.session.scalar(statement)
        if item is None:
            return False

        self.session.delete(item)
        self.session.commit()
        return True
```

Create `service/cart_service.py` with this content:

```python
from collections import OrderedDict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repository.cart_repository import CartRepository


class CartService:
    def __init__(self, session: Session):
        self.carts = CartRepository(session)

    def get_grouped_cart(self, user_id: int) -> dict:
        grouped = OrderedDict()
        for item in self.carts.list_items(user_id):
            merchant = self.carts.get_merchant(item.merchant_id)
            bucket = grouped.setdefault(
                item.merchant_id,
                {
                    "merchant_id": item.merchant_id,
                    "merchant_name": merchant.name if merchant else f"merchant-{item.merchant_id}",
                    "items": [],
                    "subtotal": 0.0,
                },
            )
            dish = self.carts.get_dish(item.dish_id)
            row_total = float(item.unit_price_snapshot) * item.quantity
            bucket["items"].append(
                {
                    "dish_id": item.dish_id,
                    "dish_name": dish.name if dish else f"dish-{item.dish_id}",
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price_snapshot),
                }
            )
            bucket["subtotal"] += row_total

        goods_amount = sum(group["subtotal"] for group in grouped.values())
        return {"items": list(grouped.values()), "goods_amount": goods_amount}

    def add_item(self, user_id: int, payload) -> dict:
        try:
            item = self.carts.upsert_item(user_id, payload.dish_id, payload.quantity)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dish not found")
        return {"success": True, "dish_id": item.dish_id, "quantity": item.quantity}

    def remove_item(self, user_id: int, dish_id: int) -> dict:
        deleted = self.carts.remove_item(user_id, dish_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cart item not found")
        return {"success": True, "dish_id": dish_id}
```

- [ ] **Step 4: Create the cart route module and register it**

Create `api/routes/cart.py` with this content:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.deps import get_current_user
from api.models.user import User
from api.schemas import CartMutationRequest
from service.cart_service import CartService


router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("")
def get_cart(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return CartService(session).get_grouped_cart(current_user.id)


@router.post("/items")
def add_item(
    payload: CartMutationRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return CartService(session).add_item(current_user.id, payload)


@router.delete("/items/{dish_id}")
def remove_item(
    dish_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return CartService(session).remove_item(current_user.id, dish_id)
```

Update `api/routes/__init__.py` to this content:

```python
from api.routes.address import router as address_router
from api.routes.auth import router as auth_router
from api.routes.cart import router as cart_router
from api.routes.catalog import router as catalog_router
from api.routes.health import router as health_router

__all__ = ["address_router", "auth_router", "cart_router", "catalog_router", "health_router"]
```

Update `api/main.py` includes to this block:

```python
from api.routes import address_router, auth_router, cart_router, catalog_router, health_router

app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(address_router)
app.include_router(cart_router)
app.include_router(health_router)
```

- [ ] **Step 5: Re-run the cart route test**

Run:

```bash
python -m pytest tests/api/test_cart_routes.py -v
```

Expected:

```txt
tests/api/test_cart_routes.py::test_get_cart_returns_grouped_merchants PASSED
```

- [ ] **Step 6: Commit the cart task**

Run:

```bash
git add repository/cart_repository.py service/cart_service.py api/routes/cart.py api/routes/__init__.py api/main.py tests/api/test_cart_routes.py
git commit -m "feat: add grouped cart route"
```

### Task 8: Add checkout preview, split-order creation, mock payment, and order-query APIs

**Files:**
- Create: `repository/order_repository.py`
- Create: `service/order_service.py`
- Create: `api/routes/orders.py`
- Modify: `api/routes/__init__.py`
- Modify: `api/main.py`
- Test: `tests/api/test_order_routes.py`

- [ ] **Step 1: Write the failing order route tests**

Create `tests/api/test_order_routes.py` with this content:

```python
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app, raise_server_exceptions=False)



def test_checkout_preview_submit_mock_pay_and_query_orders(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routes.orders.OrderService.preview_checkout",
        lambda self, user_id, address_id: {
            "goods_amount": 88.0,
            "delivery_amount": 8.0,
            "payable_amount": 96.0,
            "merchant_count": 2,
        },
    )
    monkeypatch.setattr(
        "api.routes.orders.OrderService.submit_checkout",
        lambda self, user_id, address_id: {
            "checkout_order_id": 3,
            "payment_status": "pending_payment",
            "order_status": "pending_payment",
            "merchant_orders": [
                {"merchant_id": 1, "order_status": "pending_payment"},
                {"merchant_id": 2, "order_status": "pending_payment"},
            ],
        },
    )
    monkeypatch.setattr(
        "api.routes.orders.OrderService.mock_pay",
        lambda self, checkout_order_id: {
            "checkout_order_id": checkout_order_id,
            "payment_status": "paid",
            "order_status": "paid",
        },
    )
    monkeypatch.setattr(
        "api.routes.orders.OrderService.list_orders",
        lambda self, user_id: [
            {
                "checkout_order_id": 3,
                "payment_status": "paid",
                "order_status": "paid",
                "payable_amount": 96.0,
            }
        ],
    )
    monkeypatch.setattr(
        "api.routes.orders.OrderService.get_order_detail",
        lambda self, user_id, checkout_order_id: {
            "checkout_order_id": checkout_order_id,
            "payment_status": "paid",
            "order_status": "paid",
            "merchant_orders": [
                {
                    "merchant_order_id": 10,
                    "merchant_id": 1,
                    "order_status": "paid",
                    "items": [{"dish_id": 11, "dish_name": "鱼香肉丝", "quantity": 2}],
                },
                {
                    "merchant_order_id": 11,
                    "merchant_id": 2,
                    "order_status": "paid",
                    "items": [{"dish_id": 21, "dish_name": "招牌牛肉饭", "quantity": 1}],
                },
            ],
        },
    )
    monkeypatch.setattr("api.routes.orders.get_current_user", lambda: type("User", (), {"id": 5})())

    preview_response = client.post("/orders/preview", json={"address_id": 1})
    assert preview_response.status_code == 200
    assert preview_response.json()["merchant_count"] == 2

    submit_response = client.post("/orders", json={"address_id": 1})
    assert submit_response.status_code == 201
    assert len(submit_response.json()["merchant_orders"]) == 2

    pay_response = client.post("/orders/mock-pay", json={"checkout_order_id": 3})
    assert pay_response.status_code == 200
    assert pay_response.json()["payment_status"] == "paid"

    list_response = client.get("/orders")
    assert list_response.status_code == 200
    assert list_response.json()[0]["checkout_order_id"] == 3

    detail_response = client.get("/orders/3")
    assert detail_response.status_code == 200
    assert len(detail_response.json()["merchant_orders"]) == 2
```

- [ ] **Step 2: Run the order route tests to verify they fail**

Run:

```bash
python -m pytest tests/api/test_order_routes.py -v
```

Expected: FAIL because `/orders/preview`, `/orders`, `/orders/{checkout_order_id}`, and `/orders/mock-pay` do not exist yet.

- [ ] **Step 3: Create the order repository and service**

Create `repository/order_repository.py` with this content:

```python
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.cart import CartItem
from api.models.order import CheckoutOrder, DeliveryQuote, MerchantOrder, OrderItem, PaymentRecord
from api.models.user import UserAddress


class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_cart_items(self, user_id: int) -> list[CartItem]:
        statement = select(CartItem).where(CartItem.user_id == user_id).order_by(CartItem.merchant_id.asc(), CartItem.id.asc())
        return list(self.session.scalars(statement))

    def get_address(self, user_id: int, address_id: int) -> UserAddress | None:
        statement = select(UserAddress).where(UserAddress.user_id == user_id, UserAddress.id == address_id)
        return self.session.scalar(statement)

    def create_checkout_order(self, user_id: int, address_snapshot: str, goods_amount: float, delivery_amount: float, payable_amount: float) -> CheckoutOrder:
        order = CheckoutOrder(
            user_id=user_id,
            address_snapshot=address_snapshot,
            goods_amount=goods_amount,
            delivery_amount=delivery_amount,
            payable_amount=payable_amount,
        )
        self.session.add(order)
        self.session.flush()
        return order

    def create_merchant_order(self, checkout_order_id: int, merchant_id: int, goods_amount: float, delivery_amount: float, payable_amount: float) -> MerchantOrder:
        order = MerchantOrder(
            checkout_order_id=checkout_order_id,
            merchant_id=merchant_id,
            goods_amount=goods_amount,
            delivery_amount=delivery_amount,
            payable_amount=payable_amount,
        )
        self.session.add(order)
        self.session.flush()
        return order

    def create_order_item(self, merchant_order_id: int, dish_id: int, dish_name_snapshot: str, quantity: int, unit_price_snapshot: float) -> None:
        self.session.add(
            OrderItem(
                merchant_order_id=merchant_order_id,
                dish_id=dish_id,
                dish_name_snapshot=dish_name_snapshot,
                quantity=quantity,
                unit_price_snapshot=unit_price_snapshot,
            )
        )

    def create_delivery_quote(self, checkout_order_id: int, merchant_id: int, estimated_minutes: int, delivery_fee: float) -> None:
        self.session.add(
            DeliveryQuote(
                checkout_order_id=checkout_order_id,
                merchant_id=merchant_id,
                in_range=True,
                distance_meters=1800,
                estimated_minutes=estimated_minutes,
                delivery_fee=delivery_fee,
                message="within delivery range",
            )
        )

    def get_checkout_order(self, checkout_order_id: int) -> CheckoutOrder | None:
        return self.session.get(CheckoutOrder, checkout_order_id)

    def get_checkout_order_for_user(self, user_id: int, checkout_order_id: int) -> CheckoutOrder | None:
        statement = select(CheckoutOrder).where(CheckoutOrder.user_id == user_id, CheckoutOrder.id == checkout_order_id)
        return self.session.scalar(statement)

    def list_checkout_orders(self, user_id: int) -> list[CheckoutOrder]:
        statement = select(CheckoutOrder).where(CheckoutOrder.user_id == user_id).order_by(CheckoutOrder.id.desc())
        return list(self.session.scalars(statement))

    def list_merchant_orders(self, checkout_order_id: int) -> list[MerchantOrder]:
        statement = select(MerchantOrder).where(MerchantOrder.checkout_order_id == checkout_order_id).order_by(MerchantOrder.id.asc())
        return list(self.session.scalars(statement))

    def list_order_items(self, merchant_order_id: int) -> list[OrderItem]:
        statement = select(OrderItem).where(OrderItem.merchant_order_id == merchant_order_id).order_by(OrderItem.id.asc())
        return list(self.session.scalars(statement))

    def create_payment_record(self, checkout_order_id: int) -> PaymentRecord:
        payment = PaymentRecord(checkout_order_id=checkout_order_id, request_no=f"mock-{uuid4().hex[:16]}")
        self.session.add(payment)
        self.session.flush()
        return payment
```

Create `service/order_service.py` with this content:

```python
from collections import OrderedDict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repository.order_repository import OrderRepository


class OrderService:
    def __init__(self, session: Session):
        self.session = session
        self.orders = OrderRepository(session)

    def _group_items(self, items):
        grouped = OrderedDict()
        for item in items:
            grouped.setdefault(item.merchant_id, []).append(item)
        return grouped

    def preview_checkout(self, user_id: int, address_id: int) -> dict:
        address = self.orders.get_address(user_id, address_id)
        if address is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="address not found")

        items = self.orders.list_cart_items(user_id)
        if not items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cart is empty")

        grouped = self._group_items(items)
        goods_amount = sum(float(item.unit_price_snapshot) * item.quantity for item in items)
        delivery_amount = float(len(grouped) * 4)
        return {
            "goods_amount": goods_amount,
            "delivery_amount": delivery_amount,
            "payable_amount": goods_amount + delivery_amount,
            "merchant_count": len(grouped),
        }

    def submit_checkout(self, user_id: int, address_id: int) -> dict:
        preview = self.preview_checkout(user_id, address_id)
        address = self.orders.get_address(user_id, address_id)
        items = self.orders.list_cart_items(user_id)
        grouped = self._group_items(items)

        checkout_order = self.orders.create_checkout_order(
            user_id=user_id,
            address_snapshot=f"{address.city}{address.district}{address.detail_address}",
            goods_amount=preview["goods_amount"],
            delivery_amount=preview["delivery_amount"],
            payable_amount=preview["payable_amount"],
        )

        merchant_orders = []
        for merchant_id, merchant_items in grouped.items():
            merchant_goods = sum(float(item.unit_price_snapshot) * item.quantity for item in merchant_items)
            merchant_order = self.orders.create_merchant_order(
                checkout_order_id=checkout_order.id,
                merchant_id=merchant_id,
                goods_amount=merchant_goods,
                delivery_amount=4.0,
                payable_amount=merchant_goods + 4.0,
            )
            merchant_orders.append({"merchant_id": merchant_id, "order_status": merchant_order.order_status})
            self.orders.create_delivery_quote(checkout_order.id, merchant_id, estimated_minutes=30, delivery_fee=4.0)
            for item in merchant_items:
                self.orders.create_order_item(
                    merchant_order_id=merchant_order.id,
                    dish_id=item.dish_id,
                    dish_name_snapshot=f"dish-{item.dish_id}",
                    quantity=item.quantity,
                    unit_price_snapshot=float(item.unit_price_snapshot),
                )

        self.session.commit()
        return {
            "checkout_order_id": checkout_order.id,
            "payment_status": checkout_order.payment_status,
            "order_status": checkout_order.order_status,
            "merchant_orders": merchant_orders,
        }

    def mock_pay(self, checkout_order_id: int) -> dict:
        order = self.orders.get_checkout_order(checkout_order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="checkout order not found")

        self.orders.create_payment_record(checkout_order_id=order.id)
        order.payment_status = "paid"
        order.order_status = "paid"
        for merchant_order in self.orders.list_merchant_orders(order.id):
            merchant_order.order_status = "paid"
        self.session.commit()
        return {"checkout_order_id": order.id, "payment_status": order.payment_status, "order_status": order.order_status}

    def list_orders(self, user_id: int) -> list[dict]:
        return [
            {
                "checkout_order_id": order.id,
                "payment_status": order.payment_status,
                "order_status": order.order_status,
                "payable_amount": float(order.payable_amount),
            }
            for order in self.orders.list_checkout_orders(user_id)
        ]

    def get_order_detail(self, user_id: int, checkout_order_id: int) -> dict:
        order = self.orders.get_checkout_order_for_user(user_id, checkout_order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order not found")

        merchant_orders = []
        for merchant_order in self.orders.list_merchant_orders(order.id):
            items = self.orders.list_order_items(merchant_order.id)
            merchant_orders.append(
                {
                    "merchant_order_id": merchant_order.id,
                    "merchant_id": merchant_order.merchant_id,
                    "order_status": merchant_order.order_status,
                    "items": [
                        {
                            "dish_id": item.dish_id,
                            "dish_name": item.dish_name_snapshot,
                            "quantity": item.quantity,
                        }
                        for item in items
                    ],
                }
            )

        return {
            "checkout_order_id": order.id,
            "payment_status": order.payment_status,
            "order_status": order.order_status,
            "merchant_orders": merchant_orders,
        }
```

- [ ] **Step 4: Create the order route module and register it**

Create `api/routes/orders.py` with this content:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.deps import get_current_user
from api.models.user import User
from api.schemas import CheckoutPreviewRequest, MockPayRequest
from service.order_service import OrderService


router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("")
def list_orders(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return OrderService(session).list_orders(current_user.id)


@router.get("/{checkout_order_id}")
def get_order_detail(
    checkout_order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return OrderService(session).get_order_detail(current_user.id, checkout_order_id)


@router.post("/preview")
def preview_checkout(
    payload: CheckoutPreviewRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return OrderService(session).preview_checkout(current_user.id, payload.address_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_checkout(
    payload: CheckoutPreviewRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return OrderService(session).submit_checkout(current_user.id, payload.address_id)


@router.post("/mock-pay")
def mock_pay(payload: MockPayRequest, session: Session = Depends(get_db_session)):
    return OrderService(session).mock_pay(payload.checkout_order_id)
```

Update `api/routes/__init__.py` to this content:

```python
from api.routes.address import router as address_router
from api.routes.auth import router as auth_router
from api.routes.cart import router as cart_router
from api.routes.catalog import router as catalog_router
from api.routes.health import router as health_router
from api.routes.orders import router as orders_router

__all__ = [
    "address_router",
    "auth_router",
    "cart_router",
    "catalog_router",
    "health_router",
    "orders_router",
]
```

Update `api/main.py` includes to this block:

```python
from api.routes import address_router, auth_router, cart_router, catalog_router, health_router, orders_router

app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(address_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(health_router)
```

- [ ] **Step 5: Re-run the order route tests**

Run:

```bash
python -m pytest tests/api/test_order_routes.py -v
```

Expected:

```txt
tests/api/test_order_routes.py::test_checkout_preview_submit_mock_pay_and_query_orders PASSED
```

- [ ] **Step 6: Commit the order task**

Run:

```bash
git add repository/order_repository.py service/order_service.py api/routes/orders.py api/routes/__init__.py api/main.py tests/api/test_order_routes.py
git commit -m "feat: add checkout and order query routes"
```

### Task 9: Add agent-context placeholder APIs

**Files:**
- Create: `api/routes/agent_context.py`
- Modify: `api/routes/__init__.py`
- Modify: `api/main.py`
- Test: `tests/api/test_agent_context_routes.py`

- [ ] **Step 1: Write the failing agent-context route test**

Create `tests/api/test_agent_context_routes.py` with this content:

```python
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app, raise_server_exceptions=False)



def test_agent_context_route_exposes_structured_placeholders(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routes.agent_context.build_agent_context",
        lambda user_id: {
            "user_id": user_id,
            "addresses": [],
            "cart": {"items": [], "goods_amount": 0.0},
            "recent_orders": [],
            "merchants": [],
        },
    )

    response = client.get("/agent-context/users/9")

    assert response.status_code == 200
    assert response.json()["user_id"] == 9
    assert response.json()["cart"]["goods_amount"] == 0.0
    assert response.json()["merchants"] == []
```

- [ ] **Step 2: Run the agent-context route test to verify it fails**

Run:

```bash
python -m pytest tests/api/test_agent_context_routes.py -v
```

Expected: FAIL because the route does not exist yet.

- [ ] **Step 3: Create the agent-context route module and register it**

Create `api/routes/agent_context.py` with this content:

```python
from fastapi import APIRouter


router = APIRouter(prefix="/agent-context", tags=["agent-context"])



def build_agent_context(user_id: int) -> dict:
    return {
        "user_id": user_id,
        "addresses": [],
        "cart": {"items": [], "goods_amount": 0.0},
        "recent_orders": [],
        "merchants": [],
    }


@router.get("/users/{user_id}")
def get_agent_context(user_id: int):
    return build_agent_context(user_id)
```

Update `api/routes/__init__.py` to this content:

```python
from api.routes.address import router as address_router
from api.routes.agent_context import router as agent_context_router
from api.routes.auth import router as auth_router
from api.routes.cart import router as cart_router
from api.routes.catalog import router as catalog_router
from api.routes.health import router as health_router
from api.routes.orders import router as orders_router

__all__ = [
    "address_router",
    "agent_context_router",
    "auth_router",
    "cart_router",
    "catalog_router",
    "health_router",
    "orders_router",
]
```

Update `api/main.py` includes to this block:

```python
from api.routes import address_router, agent_context_router, auth_router, cart_router, catalog_router, health_router, orders_router

app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(address_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(agent_context_router)
app.include_router(health_router)
```

- [ ] **Step 4: Re-run the agent-context route test**

Run:

```bash
python -m pytest tests/api/test_agent_context_routes.py -v
```

Expected:

```txt
tests/api/test_agent_context_routes.py::test_agent_context_route_exposes_structured_placeholders PASSED
```

- [ ] **Step 5: Commit the agent-context task**

Run:

```bash
git add api/routes/agent_context.py api/routes/__init__.py api/main.py tests/api/test_agent_context_routes.py
git commit -m "feat: reserve agent context api"
```

### Task 10: Add Alembic migration and deterministic seed-data tooling

**Files:**
- Create: `alembic.ini`
- Create: `database/migrations/env.py`
- Create: `database/migrations/versions/20260420_01_phase1_foundation.py`
- Create: `database/seeds/merchant_seed_data.py`
- Create: `tools/seed_demo_data.py`
- Create: `tools/seed_catalog_data.py`
- Create: `.env.example`
- Modify: `README.md`
- Test: `tests/test_seed_payload.py`

- [ ] **Step 1: Write the failing seed payload test**

Create `tests/test_seed_payload.py` with this content:

```python
from database.seeds.merchant_seed_data import MERCHANT_SEED_DATA



def test_seed_payload_contains_realistic_multi_merchant_data() -> None:
    assert len(MERCHANT_SEED_DATA) == 20
    assert len({merchant["district"] for merchant in MERCHANT_SEED_DATA}) == 5
    assert all(len(merchant["categories"]) == 2 for merchant in MERCHANT_SEED_DATA)
    assert all(sum(len(category["dishes"]) for category in merchant["categories"]) == 10 for merchant in MERCHANT_SEED_DATA)
```

- [ ] **Step 2: Run the seed payload test to verify it fails**

Run:

```bash
python -m pytest tests/test_seed_payload.py -v
```

Expected: FAIL because the seed module does not exist yet.

- [ ] **Step 3: Create the deterministic merchant seed payload module**

Create `database/seeds/merchant_seed_data.py` with this content:

```python
DISTRICT_POINTS = [
    {"district": "静安", "address": "南京西路 818 号", "longitude": 121.4521, "latitude": 31.2291},
    {"district": "徐汇", "address": "漕溪北路 399 号", "longitude": 121.4372, "latitude": 31.1948},
    {"district": "浦东", "address": "张杨路 1088 号", "longitude": 121.5440, "latitude": 31.2282},
    {"district": "杨浦", "address": "黄兴路 1888 号", "longitude": 121.5254, "latitude": 31.2990},
    {"district": "长宁", "address": "长宁路 1018 号", "longitude": 121.4246, "latitude": 31.2202},
]

CUISINE_PROFILES = [
    {
        "brand": "川湘小馆",
        "description": "下饭川湘家常菜",
        "delivery_radius_meters": 3200,
        "delivery_fee": 4.0,
        "min_order_amount": 20.0,
        "avg_delivery_minutes": 28,
        "rating": 4.7,
        "categories": [
            {
                "name": "招牌热菜",
                "dishes": [
                    {"name": "鱼香肉丝", "description": "酸甜开胃", "price": 28.0, "tags": "招牌,下饭", "is_recommended": True},
                    {"name": "辣子鸡", "description": "香辣酥脆", "price": 36.0, "tags": "香辣,招牌", "is_recommended": True},
                    {"name": "宫保鸡丁", "description": "甜辣平衡", "price": 30.0, "tags": "经典", "is_recommended": False},
                    {"name": "回锅肉", "description": "肥瘦相间", "price": 32.0, "tags": "热卖", "is_recommended": False},
                    {"name": "毛血旺", "description": "重辣过瘾", "price": 48.0, "tags": "重辣", "is_recommended": True},
                ],
            },
            {
                "name": "主食小吃",
                "dishes": [
                    {"name": "米饭", "description": "东北大米", "price": 2.0, "tags": "主食", "is_recommended": False},
                    {"name": "蛋炒饭", "description": "现炒粒粒分明", "price": 16.0, "tags": "主食", "is_recommended": False},
                    {"name": "酸辣粉", "description": "酸辣开胃", "price": 18.0, "tags": "小吃", "is_recommended": False},
                    {"name": "红糖糍粑", "description": "甜口收尾", "price": 12.0, "tags": "甜品", "is_recommended": False},
                    {"name": "冰粉", "description": "解辣清爽", "price": 10.0, "tags": "解辣", "is_recommended": False},
                ],
            },
        ],
    },
    {
        "brand": "轻食厨房",
        "description": "高蛋白轻食便当",
        "delivery_radius_meters": 2800,
        "delivery_fee": 5.0,
        "min_order_amount": 26.0,
        "avg_delivery_minutes": 32,
        "rating": 4.6,
        "categories": [
            {
                "name": "轻食能量碗",
                "dishes": [
                    {"name": "香煎鸡胸能量碗", "description": "高蛋白低脂", "price": 32.0, "tags": "轻食,高蛋白", "is_recommended": True},
                    {"name": "牛肉藜麦能量碗", "description": "饱腹感强", "price": 38.0, "tags": "轻食,饱腹", "is_recommended": True},
                    {"name": "三文鱼羽衣甘蓝碗", "description": "清爽鲜香", "price": 42.0, "tags": "轻食,海鲜", "is_recommended": False},
                    {"name": "烤南瓜豆腐碗", "description": "素食友好", "price": 28.0, "tags": "素食", "is_recommended": False},
                    {"name": "黑椒鸡腿蔬菜碗", "description": "微辣黑椒", "price": 34.0, "tags": "轻食,热卖", "is_recommended": False},
                ],
            },
            {
                "name": "沙拉饮品",
                "dishes": [
                    {"name": "凯撒鸡肉沙拉", "description": "经典口味", "price": 26.0, "tags": "沙拉", "is_recommended": False},
                    {"name": "牛油果鲜虾沙拉", "description": "清爽低负担", "price": 36.0, "tags": "沙拉,虾", "is_recommended": True},
                    {"name": "冷萃美式", "description": "无糖提神", "price": 14.0, "tags": "饮品", "is_recommended": False},
                    {"name": "橙香气泡水", "description": "清新解腻", "price": 12.0, "tags": "饮品", "is_recommended": False},
                    {"name": "希腊酸奶杯", "description": "早餐加餐", "price": 15.0, "tags": "甜品", "is_recommended": False},
                ],
            },
        ],
    },
    {
        "brand": "咖啡甜点站",
        "description": "咖啡与烘焙甜品",
        "delivery_radius_meters": 2500,
        "delivery_fee": 3.0,
        "min_order_amount": 18.0,
        "avg_delivery_minutes": 24,
        "rating": 4.8,
        "categories": [
            {
                "name": "咖啡",
                "dishes": [
                    {"name": "拿铁", "description": "奶香平衡", "price": 18.0, "tags": "咖啡,热卖", "is_recommended": True},
                    {"name": "美式", "description": "清爽提神", "price": 15.0, "tags": "咖啡", "is_recommended": False},
                    {"name": "燕麦拿铁", "description": "植物奶口感", "price": 22.0, "tags": "咖啡,燕麦", "is_recommended": True},
                    {"name": "摩卡", "description": "巧克力风味", "price": 24.0, "tags": "咖啡,甜感", "is_recommended": False},
                    {"name": "生椰拿铁", "description": "椰香顺滑", "price": 23.0, "tags": "咖啡,招牌", "is_recommended": True},
                ],
            },
            {
                "name": "甜点",
                "dishes": [
                    {"name": "提拉米苏", "description": "经典甜点", "price": 26.0, "tags": "甜点,招牌", "is_recommended": True},
                    {"name": "巴斯克芝士蛋糕", "description": "焦香浓郁", "price": 28.0, "tags": "甜点", "is_recommended": True},
                    {"name": "可颂", "description": "黄油香气", "price": 12.0, "tags": "烘焙", "is_recommended": False},
                    {"name": "巧克力麦芬", "description": "松软浓郁", "price": 14.0, "tags": "烘焙", "is_recommended": False},
                    {"name": "蓝莓酸奶杯", "description": "清新轻甜", "price": 16.0, "tags": "甜点", "is_recommended": False},
                ],
            },
        ],
    },
    {
        "brand": "炸鸡汉堡屋",
        "description": "炸鸡汉堡与小食拼盘",
        "delivery_radius_meters": 3000,
        "delivery_fee": 6.0,
        "min_order_amount": 29.0,
        "avg_delivery_minutes": 35,
        "rating": 4.5,
        "categories": [
            {
                "name": "汉堡套餐",
                "dishes": [
                    {"name": "经典牛肉堡", "description": "多汁厚牛肉", "price": 29.0, "tags": "汉堡,招牌", "is_recommended": True},
                    {"name": "香辣鸡腿堡", "description": "微辣酥脆", "price": 27.0, "tags": "汉堡,辣", "is_recommended": True},
                    {"name": "双层芝士牛堡", "description": "芝士浓郁", "price": 36.0, "tags": "汉堡,芝士", "is_recommended": False},
                    {"name": "鳕鱼堡", "description": "轻盈鲜香", "price": 26.0, "tags": "汉堡,海鲜", "is_recommended": False},
                    {"name": "鸡肉卷套餐", "description": "方便分享", "price": 25.0, "tags": "卷饼", "is_recommended": False},
                ],
            },
            {
                "name": "炸物小食",
                "dishes": [
                    {"name": "原味炸鸡", "description": "外酥里嫩", "price": 24.0, "tags": "炸鸡,热卖", "is_recommended": True},
                    {"name": "香辣鸡翅", "description": "辣味更足", "price": 22.0, "tags": "炸鸡,香辣", "is_recommended": True},
                    {"name": "粗薯条", "description": "现炸酥脆", "price": 12.0, "tags": "小食", "is_recommended": False},
                    {"name": "洋葱圈", "description": "适合分享", "price": 14.0, "tags": "小食", "is_recommended": False},
                    {"name": "冰可乐", "description": "解腻搭配", "price": 8.0, "tags": "饮品", "is_recommended": False},
                ],
            },
        ],
    },
]


def build_merchant_seed_data() -> list[dict]:
    merchants = []
    for district_index, district in enumerate(DISTRICT_POINTS, start=1):
        for profile_index, profile in enumerate(CUISINE_PROFILES, start=1):
            merchants.append(
                {
                    "name": f"{district['district']}{profile['brand']}{profile_index}",
                    "description": profile["description"],
                    "city": "上海",
                    "district": district["district"],
                    "address": district["address"],
                    "longitude": district["longitude"] + profile_index * 0.001,
                    "latitude": district["latitude"] + profile_index * 0.001,
                    "delivery_radius_meters": profile["delivery_radius_meters"],
                    "delivery_fee": profile["delivery_fee"],
                    "min_order_amount": profile["min_order_amount"],
                    "avg_delivery_minutes": profile["avg_delivery_minutes"] + district_index,
                    "rating": profile["rating"],
                    "categories": profile["categories"],
                }
            )
    return merchants


MERCHANT_SEED_DATA = build_merchant_seed_data()
```

- [ ] **Step 4: Create migration, seed runners, env template, and README steps**

Create `.env.example` with this content:

```env
DATABASE_URL=mysql+mysqlconnector://root:password@localhost:3306/smart_order
JWT_SECRET_KEY=smart-order-phase1-secret
```

Create `alembic.ini` with this content:

```ini
[alembic]
script_location = database/migrations
sqlalchemy.url = mysql+mysqlconnector://root:password@localhost:3306/smart_order

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers = console
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

Create `database/migrations/env.py` with this content:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from api.db import Base
from api import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Create `database/migrations/versions/20260420_01_phase1_foundation.py` with this content:

```python
from alembic import op
import sqlalchemy as sa


revision = "20260420_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "merchants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=False),
        sa.Column("district", sa.String(length=64), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("delivery_radius_meters", sa.Integer(), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("min_order_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("avg_delivery_minutes", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Numeric(3, 2), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "user_addresses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("contact_name", sa.String(length=64), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=False),
        sa.Column("district", sa.String(length=64), nullable=False),
        sa.Column("detail_address", sa.Text(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "dish_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "dishes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("dish_categories.id"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("image_url", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("tags", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("is_recommended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "carts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cart_id", sa.Integer(), sa.ForeignKey("carts.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("dish_id", sa.Integer(), sa.ForeignKey("dishes.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_snapshot", sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        "checkout_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("address_snapshot", sa.Text(), nullable=False),
        sa.Column("goods_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("delivery_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payable_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_status", sa.String(length=32), nullable=False),
        sa.Column("order_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "merchant_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checkout_order_id", sa.Integer(), sa.ForeignKey("checkout_orders.id"), nullable=False),
        sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("goods_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("delivery_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payable_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("order_status", sa.String(length=32), nullable=False),
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_order_id", sa.Integer(), sa.ForeignKey("merchant_orders.id"), nullable=False),
        sa.Column("dish_id", sa.Integer(), sa.ForeignKey("dishes.id"), nullable=False),
        sa.Column("dish_name_snapshot", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_snapshot", sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        "payment_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checkout_order_id", sa.Integer(), sa.ForeignKey("checkout_orders.id"), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("request_no", sa.String(length=64), nullable=False),
        sa.Column("payment_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("request_no"),
    )

    op.create_table(
        "delivery_quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checkout_order_id", sa.Integer(), sa.ForeignKey("checkout_orders.id"), nullable=False),
        sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("in_range", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("distance_meters", sa.Integer(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("delivery_quotes")
    op.drop_table("payment_records")
    op.drop_table("order_items")
    op.drop_table("merchant_orders")
    op.drop_table("checkout_orders")
    op.drop_table("cart_items")
    op.drop_table("carts")
    op.drop_table("dishes")
    op.drop_table("dish_categories")
    op.drop_table("user_addresses")
    op.drop_table("merchants")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
```

Create `tools/seed_catalog_data.py` with this content:

```python
from sqlalchemy.orm import Session

from api.models.catalog import Dish, DishCategory, Merchant
from database.seeds.merchant_seed_data import MERCHANT_SEED_DATA



def seed_catalog(session: Session) -> int:
    session.query(Dish).delete()
    session.query(DishCategory).delete()
    session.query(Merchant).delete()
    session.commit()

    for merchant_payload in MERCHANT_SEED_DATA:
        merchant = Merchant(
            name=merchant_payload["name"],
            description=merchant_payload["description"],
            city=merchant_payload["city"],
            district=merchant_payload["district"],
            address=merchant_payload["address"],
            longitude=merchant_payload["longitude"],
            latitude=merchant_payload["latitude"],
            delivery_radius_meters=merchant_payload["delivery_radius_meters"],
            delivery_fee=merchant_payload["delivery_fee"],
            min_order_amount=merchant_payload["min_order_amount"],
            avg_delivery_minutes=merchant_payload["avg_delivery_minutes"],
            rating=merchant_payload["rating"],
        )
        session.add(merchant)
        session.flush()

        for sort_order, category_payload in enumerate(merchant_payload["categories"], start=1):
            category = DishCategory(
                merchant_id=merchant.id,
                name=category_payload["name"],
                sort_order=sort_order,
            )
            session.add(category)
            session.flush()

            for dish_payload in category_payload["dishes"]:
                session.add(
                    Dish(
                        merchant_id=merchant.id,
                        category_id=category.id,
                        name=dish_payload["name"],
                        description=dish_payload["description"],
                        price=dish_payload["price"],
                        tags=dish_payload["tags"],
                        is_recommended=dish_payload["is_recommended"],
                    )
                )

    session.commit()
    return len(MERCHANT_SEED_DATA)
```

Create `tools/seed_demo_data.py` with this content:

```python
from api.db import SessionLocal
from api.models.user import User, UserAddress
from api.security import hash_password
from tools.seed_catalog_data import seed_catalog



def seed_demo_user(session) -> None:
    session.query(UserAddress).delete()
    session.query(User).delete()
    session.commit()

    demo_user = User(
        username="demo_user",
        password_hash=hash_password("demo123456"),
        full_name="演示用户",
        phone="13800000000",
    )
    session.add(demo_user)
    session.flush()

    session.add(
        UserAddress(
            user_id=demo_user.id,
            label="家",
            contact_name="演示用户",
            contact_phone="13800000000",
            city="上海",
            district="静安",
            detail_address="南京西路 818 号 12 楼",
            longitude=121.4521,
            latitude=31.2291,
            is_default=True,
        )
    )
    session.commit()



def main() -> None:
    session = SessionLocal()
    try:
        merchant_count = seed_catalog(session)
        seed_demo_user(session)
        print(f"Seeded {merchant_count} merchants and one demo user")
    finally:
        session.close()


if __name__ == "__main__":
    main()
```

Update `README.md` to this content:

```md
# smart_order

## Backend setup

```bash
python -m pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python tools/seed_demo_data.py
python run.py
```

Demo login:

- username: `demo_user`
- password: `demo123456`

## Frontend setup

```bash
cd ui
npm install
npm run dev
```
```

- [ ] **Step 5: Re-run the seed payload test**

Run:

```bash
python -m pytest tests/test_seed_payload.py -v
```

Expected:

```txt
tests/test_seed_payload.py::test_seed_payload_contains_realistic_multi_merchant_data PASSED
```

- [ ] **Step 6: Commit the seed and migration task**

Run:

```bash
git add alembic.ini .env.example README.md database tools tests/test_seed_payload.py
git commit -m "feat: add phase one schema migration and seed data"
```

### Task 11: Replace the frontend shell with auth, merchant browsing, and checkout pages

**Files:**
- Create: `ui/src/api/auth.js`
- Create: `ui/src/api/catalog.js`
- Create: `ui/src/api/address.js`
- Create: `ui/src/api/cart.js`
- Create: `ui/src/api/orders.js`
- Modify: `ui/src/api/index.js`
- Create: `ui/src/composables/useAuth.js`
- Create: `ui/src/composables/useCart.js`
- Create: `ui/src/utils/currency.js`
- Create: `ui/src/utils/orderStatus.js`
- Create: `ui/src/views/LoginView.vue`
- Create: `ui/src/views/MerchantListView.vue`
- Create: `ui/src/views/MerchantDetailView.vue`
- Create: `ui/src/views/CheckoutView.vue`
- Create: `ui/src/views/AddressView.vue`
- Create: `ui/src/views/OrderListView.vue`
- Create: `ui/src/views/OrderDetailView.vue`
- Modify: `ui/src/App.vue`

- [ ] **Step 1: Write the failing frontend shell verification test**

Create `tests/test_frontend_shell_files.py` with this content:

```python
from pathlib import Path


REQUIRED_FILES = [
    "ui/src/views/LoginView.vue",
    "ui/src/views/MerchantListView.vue",
    "ui/src/views/MerchantDetailView.vue",
    "ui/src/views/CheckoutView.vue",
    "ui/src/views/AddressView.vue",
    "ui/src/views/OrderListView.vue",
    "ui/src/views/OrderDetailView.vue",
]



def test_phase1_frontend_shell_files_exist_and_old_demo_is_removed() -> None:
    for relative_path in REQUIRED_FILES:
        assert Path(relative_path).exists(), relative_path

    app_contents = Path("ui/src/App.vue").read_text(encoding="utf-8")
    assert "智能点餐助手" not in app_contents
    assert "配送范围查询" not in app_contents
    assert "菜品列表" not in app_contents
    assert "smart_order 外卖平台" in app_contents
    assert "智能助手" in app_contents
```

- [ ] **Step 2: Run the frontend shell verification test to verify it fails**

Run:

```bash
python -m pytest tests/test_frontend_shell_files.py -v
```

Expected: FAIL because the new frontend view files do not exist yet and `ui/src/App.vue` still renders the old demo shell.

- [ ] **Step 3: Replace the shared Axios module with reusable domain clients**

Replace `ui/src/api/index.js` with this content:

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const accessToken = window.localStorage.getItem('smart_order_access_token')
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    throw new Error(error.response?.data?.detail || '请求失败，请稍后再试')
  },
)

export default api
```

Create `ui/src/api/auth.js` with this content:

```javascript
import api from './index'

export const register = (payload) => api.post('/auth/register', payload)
export const login = (payload) => api.post('/auth/login', payload)
```

Create `ui/src/api/catalog.js` with this content:

```javascript
import api from './index'

export const listMerchants = (district) => api.get('/catalog/merchants', { params: { district } })
export const listMerchantDishes = (merchantId) => api.get(`/catalog/merchants/${merchantId}/dishes`)
```

Create `ui/src/api/address.js` with this content:

```javascript
import api from './index'

export const listAddresses = () => api.get('/addresses')
export const createAddress = (payload) => api.post('/addresses', payload)
```

Create `ui/src/api/cart.js` with this content:

```javascript
import api from './index'

export const getCart = () => api.get('/cart')
```

Create `ui/src/api/orders.js` with this content:

```javascript
import api from './index'

export const previewCheckout = (payload) => api.post('/orders/preview', payload)
export const submitOrder = (payload) => api.post('/orders', payload)
export const mockPay = (payload) => api.post('/orders/mock-pay', payload)
export const listOrders = () => api.get('/orders')
export const getOrderDetail = (checkoutOrderId) => api.get(`/orders/${checkoutOrderId}`)
```

- [ ] **Step 4: Create the shared composables and utils**

Create `ui/src/composables/useAuth.js` with this content:

```javascript
import { ref } from 'vue'
import { login, register } from '../api/auth'

const currentUser = ref(null)
const authLoading = ref(false)

export function useAuth() {
  const loginWithPassword = async (payload) => {
    authLoading.value = true
    try {
      const result = await login(payload)
      window.localStorage.setItem('smart_order_access_token', result.access_token)
      window.localStorage.setItem('smart_order_refresh_token', result.refresh_token)
      currentUser.value = { username: payload.username }
      return result
    } finally {
      authLoading.value = false
    }
  }

  const registerWithPassword = async (payload) => register(payload)

  const logout = () => {
    window.localStorage.removeItem('smart_order_access_token')
    window.localStorage.removeItem('smart_order_refresh_token')
    currentUser.value = null
  }

  return { currentUser, authLoading, loginWithPassword, registerWithPassword, logout }
}
```

Create `ui/src/composables/useCart.js` with this content:

```javascript
import { computed, ref } from 'vue'
import { getCart } from '../api/cart'

const cart = ref({ items: [], goods_amount: 0 })
const cartLoading = ref(false)

export function useCart() {
  const refreshCart = async () => {
    cartLoading.value = true
    try {
      cart.value = await getCart()
    } finally {
      cartLoading.value = false
    }
  }

  const merchantGroups = computed(() => cart.value.items || [])

  return { cart, cartLoading, merchantGroups, refreshCart }
}
```

Create `ui/src/utils/currency.js` with this content:

```javascript
export function formatCurrency(value) {
  return `¥${Number(value || 0).toFixed(2)}`
}
```

Create `ui/src/utils/orderStatus.js` with this content:

```javascript
const labels = {
  pending_payment: '待支付',
  paid: '已支付',
  preparing: '备餐中',
  delivering: '配送中',
  completed: '已完成',
  cancelled: '已取消',
}

export function formatOrderStatus(status) {
  return labels[status] || status
}
```

- [ ] **Step 5: Create the new view components and replace `App.vue`**

Create `ui/src/views/LoginView.vue` with this content:

```vue
<template>
  <el-card>
    <template #header>账号登录</template>
    <el-form @submit.prevent>
      <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="form.password" type="password" /></el-form-item>
      <el-button type="primary" :loading="authLoading" @click="submit">登录</el-button>
    </el-form>
  </el-card>
</template>

<script setup>
import { reactive } from 'vue'
import { useAuth } from '../composables/useAuth'

const form = reactive({ username: '', password: '' })
const { authLoading, loginWithPassword } = useAuth()

const submit = async () => {
  await loginWithPassword(form)
}
</script>
```

Create `ui/src/views/MerchantListView.vue` with this content:

```vue
<template>
  <el-card>
    <template #header>商家列表</template>
    <div v-for="merchant in merchants" :key="merchant.id" class="merchant-card">
      <h3>{{ merchant.name }}</h3>
      <p>{{ merchant.description }}</p>
      <p>{{ merchant.district }} · 配送费 {{ formatCurrency(merchant.delivery_fee) }}</p>
    </div>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listMerchants } from '../api/catalog'
import { formatCurrency } from '../utils/currency'

const merchants = ref([])

onMounted(async () => {
  merchants.value = await listMerchants()
})
</script>
```

Create `ui/src/views/MerchantDetailView.vue` with this content:

```vue
<template>
  <el-card>
    <template #header>商家详情</template>
    <div v-for="dish in dishes" :key="dish.id" class="dish-card">
      <h4>{{ dish.name }}</h4>
      <p>{{ dish.description }}</p>
      <p>{{ formatCurrency(dish.price) }}</p>
    </div>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listMerchantDishes } from '../api/catalog'
import { formatCurrency } from '../utils/currency'

const dishes = ref([])

onMounted(async () => {
  dishes.value = await listMerchantDishes(1)
})
</script>
```

Create `ui/src/views/CheckoutView.vue` with this content:

```vue
<template>
  <el-card>
    <template #header>结算</template>
    <div v-for="group in merchantGroups" :key="group.merchant_id">
      <h4>{{ group.merchant_name }}</h4>
      <p>小计 {{ formatCurrency(group.subtotal) }}</p>
    </div>
    <p>商品总价 {{ formatCurrency(cart.goods_amount) }}</p>
  </el-card>
</template>

<script setup>
import { onMounted } from 'vue'
import { useCart } from '../composables/useCart'
import { formatCurrency } from '../utils/currency'

const { cart, merchantGroups, refreshCart } = useCart()

onMounted(refreshCart)
</script>
```

Create `ui/src/views/AddressView.vue` with this content:

```vue
<template>
  <el-card>
    <template #header>收货地址</template>
    <div v-for="address in addresses" :key="address.id">
      <p>{{ address.label }} · {{ address.detail_address }}</p>
    </div>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listAddresses } from '../api/address'

const addresses = ref([])

onMounted(async () => {
  addresses.value = await listAddresses()
})
</script>
```

Create `ui/src/views/OrderListView.vue` with this content:

```vue
<template>
  <el-card>
    <template #header>订单列表</template>
    <div v-for="order in orders" :key="order.checkout_order_id" class="order-card">
      <h4>订单 #{{ order.checkout_order_id }}</h4>
      <p>状态：{{ formatOrderStatus(order.order_status) }}</p>
      <p>支付：{{ formatOrderStatus(order.payment_status) }}</p>
      <p>实付：{{ formatCurrency(order.payable_amount) }}</p>
    </div>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listOrders } from '../api/orders'
import { formatCurrency } from '../utils/currency'
import { formatOrderStatus } from '../utils/orderStatus'

const orders = ref([])

onMounted(async () => {
  orders.value = await listOrders()
})
</script>
```

Create `ui/src/views/OrderDetailView.vue` with this content:

```vue
<template>
  <el-card>
    <template #header>订单详情</template>
    <div v-if="order">
      <p>订单号：#{{ order.checkout_order_id }}</p>
      <p>状态：{{ formatOrderStatus(order.order_status) }}</p>
      <div v-for="merchantOrder in order.merchant_orders" :key="merchantOrder.merchant_order_id" class="merchant-order-card">
        <h4>商家 {{ merchantOrder.merchant_id }}</h4>
        <p>子单状态：{{ formatOrderStatus(merchantOrder.order_status) }}</p>
        <ul>
          <li v-for="item in merchantOrder.items" :key="`${merchantOrder.merchant_order_id}-${item.dish_id}`">
            {{ item.dish_name }} × {{ item.quantity }}
          </li>
        </ul>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getOrderDetail } from '../api/orders'
import { formatOrderStatus } from '../utils/orderStatus'

const order = ref(null)

onMounted(async () => {
  order.value = await getOrderDetail(1)
})
</script>
```

Replace `ui/src/App.vue` with this content:

```vue
<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <h1>smart_order 外卖平台</h1>
      <p>第一期业务底座</p>
    </el-header>
    <el-main class="app-main">
      <el-row :gutter="16">
        <el-col :span="8"><LoginView /></el-col>
        <el-col :span="16"><MerchantListView /></el-col>
      </el-row>
      <el-row :gutter="16" class="section-row">
        <el-col :span="12"><MerchantDetailView /></el-col>
        <el-col :span="12"><CheckoutView /></el-col>
      </el-row>
      <el-row :gutter="16" class="section-row">
        <el-col :span="8"><AddressView /></el-col>
        <el-col :span="8"><OrderListView /></el-col>
        <el-col :span="8"><OrderDetailView /></el-col>
      </el-row>
      <el-row :gutter="16" class="section-row">
        <el-col :span="24">
          <el-card>
            <template #header>智能助手</template>
            <p>第一期仅保留接入位，第二期接入 RAG 助手。</p>
          </el-card>
        </el-col>
      </el-row>
    </el-main>
  </el-container>
</template>

<script setup>
import AddressView from './views/AddressView.vue'
import CheckoutView from './views/CheckoutView.vue'
import LoginView from './views/LoginView.vue'
import MerchantDetailView from './views/MerchantDetailView.vue'
import MerchantListView from './views/MerchantListView.vue'
import OrderDetailView from './views/OrderDetailView.vue'
import OrderListView from './views/OrderListView.vue'
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.app-header {
  background: #409eff;
  color: white;
  padding: 24px;
}

.app-main {
  padding: 24px;
}

.section-row {
  margin-top: 16px;
}
</style>
```

- [ ] **Step 6: Verify the new shell files, remove the old demo shell, and build the frontend**

Run these commands:

```bash
python -m pytest tests/test_frontend_shell_files.py -v
python -c "from pathlib import Path; contents = Path('ui/src/App.vue').read_text(encoding='utf-8'); print('智能点餐助手' in contents or '配送范围查询' in contents or '菜品列表' in contents)"
npm --prefix ui run build
```

Expected:

```txt
tests/test_frontend_shell_files.py::test_phase1_frontend_shell_files_exist_and_old_demo_is_removed PASSED
False
vite v4... building for production...
✓ built in ...
```

- [ ] **Step 7: Commit the frontend shell task**

Run:

```bash
git add ui/src/App.vue ui/src/api ui/src/composables ui/src/utils ui/src/views tests/test_frontend_shell_files.py
git commit -m "feat: add phase one delivery frontend shell"
```

### Task 12: Run the full backend regression suite and final verification

**Files:**
- Test: `tests/test_project_dependencies.py`
- Test: `tests/test_models_metadata.py`
- Test: `tests/api/test_auth_routes.py`
- Test: `tests/api/test_app_wiring.py`
- Test: `tests/api/test_catalog_routes.py`
- Test: `tests/api/test_address_routes.py`
- Test: `tests/api/test_cart_routes.py`
- Test: `tests/api/test_order_routes.py`
- Test: `tests/api/test_agent_context_routes.py`
- Test: `tests/test_seed_payload.py`
- Modify: `run.py`

- [ ] **Step 1: Update `run.py` to launch the modular app**

Replace the `uvicorn.run(...)` call in `run.py` with this block:

```python
uvicorn.run(
    "api.main:app",
    host="127.0.0.1",
    port=8000,
    reload=True,
    reload_dirs=[str(PROJECT_ROOT)],
    log_level="info",
)
```

- [ ] **Step 2: Run the full Python test suite**

Run:

```bash
python -m pytest tests -v
```

Expected: all backend and seed tests pass.

- [ ] **Step 3: Verify the FastAPI route surface**

Run:

```bash
python -c "from api.main import app; targets = {'/health', '/addresses', '/cart', '/orders', '/orders/{checkout_order_id}', '/orders/mock-pay', '/orders/preview', '/catalog/merchants', '/agent-context/users/{user_id}', '/auth/login', '/auth/me', '/auth/refresh', '/auth/register'}; print(sorted(route.path for route in app.routes if route.path in targets))"
```

Expected:

```txt
['/addresses', '/agent-context/users/{user_id}', '/auth/login', '/auth/me', '/auth/refresh', '/auth/register', '/cart', '/catalog/merchants', '/health', '/orders', '/orders/mock-pay', '/orders/preview', '/orders/{checkout_order_id}']
```

- [ ] **Step 4: Verify the frontend production build again after all API work**

Run:

```bash
npm --prefix ui run build
```

Expected: Vite production build completes successfully.

- [ ] **Step 5: Commit the final verification task**

Run:

```bash
git add run.py tests
git commit -m "test: verify phase one delivery foundation"
```

## Spec Coverage Check

- Auth, JWT/refresh-token foundation — covered by Task 3.
- Merchant and dish browsing foundation — covered by Task 5.
- Cross-merchant grouped cart — covered by Task 7.
- Address management and delivery-ready address data — covered by Task 6.
- Parent/child order foundation and mock payment — covered by Task 8.
- Agent-context reservation layer — covered by Task 9.
- Migration, seed data, and realistic merchant/dish payloads — covered by Task 10.
- User-side delivery frontend shell — covered by Task 11.
- Final route/test/build verification and app boot — covered by Task 12.

## Self-Review Notes

- The plan stays scoped to the approved first-phase foundation and does not pull in merchant backoffice, real payments, rider dispatch, or actual RAG.
- Each task lands a coherent slice that can be implemented and reviewed independently.
- The plan intentionally keeps some route behavior simple in early tasks, then verifies the integrated baseline in Task 12 before moving to phase-two assistant work.
