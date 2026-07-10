import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    """通知响应"""
    id: uuid.UUID = Field(..., description="通知ID")
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    type: str = Field(..., description="通知类型", examples=["info"])
    is_read: bool = Field(..., description="是否已读")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class NotificationCountResponse(BaseModel):
    """未读通知数量响应"""
    unread_count: int = Field(..., description="未读通知数量")
