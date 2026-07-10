import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatCreate(BaseModel):
    """创建对话请求"""
    paper_id: Optional[uuid.UUID] = Field(None, description="关联的论文ID（可选）")
    title: str = Field(..., min_length=1, max_length=200, description="对话标题", examples=["关于 Attention 论文的讨论"])


class MessageCreate(BaseModel):
    """发送消息请求"""
    content: str = Field(..., min_length=1, description="消息内容", examples=["这篇论文的主要贡献是什么？"])


class MessageResponse(BaseModel):
    """消息详情响应"""
    id: uuid.UUID = Field(..., description="消息ID")
    role: str = Field(..., description="角色：user / assistant", examples=["user"])
    content: str = Field(..., description="消息内容")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    """对话信息响应"""
    id: uuid.UUID = Field(..., description="对话ID")
    title: str = Field(..., description="对话标题", examples=["关于 Attention 论文的讨论"])
    paper_id: Optional[uuid.UUID] = Field(None, description="关联的论文ID")
    created_at: datetime = Field(..., description="创建时间")
    messages: list[MessageResponse] = Field(default_factory=list, description="消息列表")

    model_config = {"from_attributes": True}


class ChatListResponse(BaseModel):
    """对话列表响应（不含消息）"""
    id: uuid.UUID = Field(..., description="对话ID")
    title: str = Field(..., description="对话标题")
    paper_id: Optional[uuid.UUID] = Field(None, description="关联的论文ID")
    created_at: datetime = Field(..., description="创建时间")
    last_message: Optional[str] = Field(None, description="最后一条消息内容")

    model_config = {"from_attributes": True}
