from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    """通用 API 响应包装"""
    success: bool = Field(..., description="请求是否成功", examples=[True])
    data: Optional[T] = Field(None, description="响应数据")
    message: str = Field(default="ok", description="响应消息", examples=["ok"])


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: list[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量", examples=[100])
    page: int = Field(..., description="当前页码", examples=[1])
    per_page: int = Field(..., description="每页数量", examples=[20])
