import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_DATABASE_PATH = PROJECT_ROOT / "test_address_routes.db"
TEST_DATABASE_PATH.unlink(missing_ok=True)

os.environ["JWT_SECRET_KEY"] = "test-phase1-secret"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

from api.db import engine
from api.main import app
from api.models.user import User, UserAddress


User.__table__.create(bind=engine, checkfirst=True)
UserAddress.__table__.create(bind=engine, checkfirst=True)
client = TestClient(app, raise_server_exceptions=False)


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


def test_addresses_register_as_single_route_for_get_and_post() -> None:
    address_routes = [route for route in app.routes if route.path == "/addresses"]

    assert len(address_routes) == 1
    assert {"GET", "POST"}.issubset(address_routes[0].methods)


def test_addresses_openapi_keeps_distinct_get_and_post_metadata() -> None:
    operations = app.openapi()["paths"]["/addresses"]

    assert operations["get"]["operationId"] != operations["post"]["operationId"]
    assert "requestBody" not in operations["get"]
    assert operations["get"]["responses"]["200"]["content"]["application/json"]["schema"]["type"] == "array"
    assert operations["get"]["responses"]["200"]["content"]["application/json"]["schema"]["items"]["$ref"].endswith("/AddressResponse")
    assert "201" in operations["post"]["responses"]
    assert operations["post"]["responses"]["201"]["content"]["application/json"]["schema"]["$ref"].endswith("/AddressResponse")


def test_address_crud_requires_authentication() -> None:
    response = client.get("/addresses")

    assert response.status_code == 401


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
    first_id = first_response.json()["id"]

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
    second_id = second_response.json()["id"]

    list_response = client.get("/addresses", headers=headers)

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": first_id,
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
            "id": second_id,
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
    created_id = create_response.json()["id"]

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
            "id": created_id,
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
