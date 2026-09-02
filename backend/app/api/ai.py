"""AI chat endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services.ai import AIError, chat, chat_stream, provider_status

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _translate(e: AIError):
    raise HTTPException(status_code=e.status, detail=e.message) from e


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None


class ChatResponse(BaseModel):
    response: str


class StatusResponse(BaseModel):
    configured: bool
    provider: str | None = None
    model: str | None = None


@router.get("/status", response_model=StatusResponse)
def status_endpoint(
    db=Depends(get_db),
    user: User = Depends(get_current_user),
):
    info = provider_status()
    return StatusResponse(
        configured=info["configured"],
        provider=info.get("provider"),
        model=info.get("model"),
    )


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    body: ChatRequest,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        response = chat(db, body.message, body.history)
    except AIError as e:
        _translate(e)
    return ChatResponse(response=response)


@router.post("/chat/stream")
def chat_stream_endpoint(
    body: ChatRequest,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
):
    def gen():
        try:
            yield from chat_stream(db, body.message, body.history)
        except AIError as e:
            yield f'{{"type":"error","message":{json.dumps(e.message)}}}' + "\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
