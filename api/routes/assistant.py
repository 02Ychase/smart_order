from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.schemas import AssistantChatRequest, AssistantChatResponse, AssistantHealthResponse
from service.assistant_service import AssistantService, build_assistant_health


router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
def chat(
    request: AssistantChatRequest,
    session: Session = Depends(get_db_session),
) -> AssistantChatResponse:
    return AssistantService(session).chat(request)


@router.get("/health", response_model=AssistantHealthResponse)
def assistant_health() -> AssistantHealthResponse:
    return build_assistant_health()
