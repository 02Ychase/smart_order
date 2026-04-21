import os

from fastapi.testclient import TestClient

os.environ["JWT_SECRET_KEY"] = "test-phase1-secret"
os.environ["DATABASE_URL"] = "sqlite:///./test_app_wiring.db"

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
