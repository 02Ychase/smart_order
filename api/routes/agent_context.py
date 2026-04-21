from typing import Any

from fastapi import APIRouter


router = APIRouter(prefix="/agent-context", tags=["agent-context"])



def build_agent_context(user_id: int) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "addresses": [],
        "cart": {"items": [], "goods_amount": 0.0},
        "recent_orders": [],
        "merchants": [],
    }


@router.get("/users/{user_id}")
def get_agent_context(user_id: int) -> dict[str, Any]:
    return build_agent_context(user_id)
