import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from api.db import get_db_session
from api.deps import get_current_user
from api.models.user import User
from api.schemas import AssistantChatRequest, AssistantChatResponse, AssistantHealthResponse
from service.assistant_service import AssistantService, build_assistant_health


router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
async def chat(
    request: AssistantChatRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AssistantChatResponse:
    # Identity comes from the authenticated token, never from the request body.
    request.user_id = current_user.id
    return await AssistantService(session).async_chat(request)


@router.post("/chat/stream")
async def chat_stream(
    request: AssistantChatRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    from service.assistant_stream_service import AssistantStreamService

    service = AssistantStreamService(session)

    async def event_generator():
        async for chunk in service.stream_chat_tokens(
            message=request.message,
            session_id=request.session_id,
            user_id=current_user.id,
        ):
            yield {"event": chunk["type"], "data": json.dumps(chunk, ensure_ascii=False)}

    return EventSourceResponse(event_generator())


@router.get("/health", response_model=AssistantHealthResponse)
def assistant_health() -> AssistantHealthResponse:
    return build_assistant_health()
