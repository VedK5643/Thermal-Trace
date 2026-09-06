"""
FastAPI Chat Router for ThermalTrace AI Intelligence Assistant.
Exposes POST /api/v1/chat.
"""
import uuid
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.llm.provider import get_llm_provider
from app.services.llm.tools import ToolExecutor
from app.services.auth import get_session, check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User prompt or query message")
    conversation_id: Optional[str] = Field(None, alias="conversationId", serialization_alias="conversationId")
    history: Optional[List[ChatMessage]] = Field(default_factory=list, description="Prior conversation messages")


class ChatResponse(BaseModel):
    message: str = Field(..., description="LLM grounded text response")
    conversation_id: str = Field(..., alias="conversationId", serialization_alias="conversationId")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, alias="toolCalls", serialization_alias="toolCalls")
    action: Optional[Dict[str, Any]] = Field(None, description="Optional UI action instruction (e.g. focus_hotspot, apply_filter)")
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/chat", response_model=ChatResponse, response_model_by_alias=True)
async def chat_endpoint(
    request: ChatRequest,
    http_req: Request,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """
    POST /api/v1/chat
    Processes user query using LLM provider and backend tool calling architecture.
    Applies server-side rate limits / quotas via Redis.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session = get_session(authorization) if authorization else None
    is_authenticated = session is not None
    client_ip = http_req.client.host if http_req.client else "127.0.0.1"
    identifier = session["user_id"] if session else f"ip:{client_ip}"

    allowed, limit_msg = await check_rate_limit(identifier, is_ai_endpoint=True, is_authenticated=is_authenticated)
    if not allowed:
        raise HTTPException(status_code=429, detail="AI usage limit reached. Please try again later.")

    conv_id = request.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"

    # Build conversation payload
    messages_payload = []
    if request.history:
        for msg in request.history:
            messages_payload.append({"role": msg.role, "content": msg.content})
    messages_payload.append({"role": "user", "content": request.message})

    # Instantiate provider & executor
    provider = get_llm_provider()
    executor = ToolExecutor(db)

    # Run chat turn
    res = await provider.chat(messages_payload, executor)

    return ChatResponse(
        message=res.get("message", "No response text."),
        conversationId=conv_id,
        toolCalls=res.get("tool_calls", []),
        metadata=res.get("metadata", {})
    )
