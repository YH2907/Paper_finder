"""对话路由"""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.chat import (
    ChatCreate,
    ChatListResponse,
    ChatResponse,
    MessageCreate,
    MessageResponse,
)
from app.schemas.common import ResponseBase
from app.services.chat_service import ChatService
from app.services.ai.router import AIRouter
from app.services.ai.groq import GroqService
from app.services.ai.gemini import GeminiService
from app.services.ai.mock import MockAIService
from app.config import settings

router = APIRouter(prefix="/chats", tags=["对话"])


def _build_ai_router() -> AIRouter:
    """构建 AI 路由器

    如果没有配置 AI API Key，使用 Mock 服务
    """
    if settings.has_ai_configured:
        primary = GroqService(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
        fallback = GeminiService(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    else:
        primary = MockAIService()
        fallback = MockAIService()
    return AIRouter(primary=primary, fallback=fallback)


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    """获取对话服务实例"""
    ai_router = _build_ai_router()
    return ChatService(db=db, ai_router=ai_router)


@router.get("/", response_model=ResponseBase[list[ChatListResponse]])
async def get_chats(
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """获取当前用户的所有对话"""
    chats = chat_service.get_chats(current_user.id)

    return ResponseBase(
        success=True,
        data=chats,
        message="获取对话列表成功",
    )


@router.post("/", response_model=ResponseBase[ChatResponse], status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_in: ChatCreate,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """创建新对话"""
    chat = chat_service.create_chat(
        user_id=current_user.id,
        title=chat_in.title,
        paper_id=chat_in.paper_id,
    )

    return ResponseBase(
        success=True,
        data=chat,
        message="创建对话成功",
    )


@router.get("/{chat_id}", response_model=ResponseBase[ChatResponse])
async def get_chat(
    chat_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """获取对话详情（含消息列表）"""
    chat = chat_service.get_chat(chat_id, current_user.id)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在或无权访问",
        )

    return ResponseBase(
        success=True,
        data=chat,
        message="获取对话详情成功",
    )


@router.post("/{chat_id}/messages", response_model=ResponseBase[MessageResponse])
async def send_message(
    chat_id: uuid.UUID,
    message_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """发送消息（非流式）"""
    result = await chat_service.send_message(
        chat_id=chat_id,
        user_id=current_user.id,
        content=message_in.content,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在或无权访问",
        )

    return ResponseBase(
        success=True,
        data=result,
        message="发送消息成功",
    )


@router.post("/{chat_id}/messages/stream")
async def send_message_stream(
    chat_id: uuid.UUID,
    message_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """发送消息（流式，SSE）

    返回 Server-Sent Events 流，事件类型：
    - token: AI 回复的文本片段
    - done: 流结束，包含 message_id
    - error: 错误信息
    """
    # 先验证对话存在且有权限
    chat = chat_service.get_chat(chat_id, current_user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在或无权访问",
        )

    async def event_generator():
        async for chunk in chat_service.send_message_stream(
            chat_id=chat_id,
            user_id=current_user.id,
            content=message_in.content,
        ):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """删除对话"""
    success = chat_service.delete_chat(chat_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在或无权访问",
        )

    return None
