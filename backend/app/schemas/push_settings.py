"""推送设置相关请求/响应模型"""

from typing import Optional
from pydantic import BaseModel, Field


class PushSettingsResponse(BaseModel):
    """推送设置响应"""
    push_enabled: bool = Field(True, description="是否启用推送")
    push_frequency: str = Field("daily", description="推送频率: daily, weekly, monthly")
    push_time: str = Field("09:00", description="推送时间 HH:MM")
    push_count: int = Field(10, ge=1, le=50, description="每次推送论文数量")


class PushSettingsUpdate(BaseModel):
    """推送设置更新请求"""
    push_enabled: Optional[bool] = Field(None, description="是否启用推送")
    push_frequency: Optional[str] = Field(None, description="推送频率: daily, weekly, monthly")
    push_time: Optional[str] = Field(None, description="推送时间 HH:MM")
    push_count: Optional[int] = Field(None, ge=1, le=50, description="每次推送论文数量")
