import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_DATABASE_PATH = PROJECT_ROOT / "test_agent_context_routes.db"
TEST_DATABASE_PATH.unlink(missing_ok=True)

os.environ["JWT_SECRET_KEY"] = "test-phase1-secret"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

from api.main import app


client = TestClient(app, raise_server_exceptions=False)



def test_get_agent_context_returns_placeholder_contract(monkeypatch) -> None:
    expected_payload = {
        "user_id": 9,
        "addresses": [],
        "cart": {"items": [], "goods_amount": 0.0},
        "recent_orders": [],
        "merchants": [],
    }

    monkeypatch.setattr(
        "api.routes.agent_context.build_agent_context",
        lambda user_id: expected_payload,
    )

    response = client.get("/agent-context/users/9")

    assert response.status_code == 200
    assert response.json() == expected_payload
