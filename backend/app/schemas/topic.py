import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TopicCreate(BaseModel):
    """创建研究主题请求"""
    name: str = Field(..., min_length=1, max_length=200, description="主题名称", examples=["LLM Agent"])
    keywords: list[str] = Field(..., min_length=1, description="关键词列表", examples=[["LLM", "agent", "tool use"]])
    exclude_keywords: list[str] = Field(default_factory=list, description="排除关键词", examples=[["survey", "review"]])
    description: Optional[str] = Field(None, max_length=1000, description="主题描述：简要描述研究背景和方向")
    problem_statement: Optional[str] = Field(None, max_length=2000, description="问题陈述：描述你想要解决的具体问题")


class TopicUpdate(BaseModel):
    """更新研究主题请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="主题名称")
    keywords: Optional[list[str]] = Field(None, min_length=1, description="关键词列表")
    exclude_keywords: Optional[list[str]] = Field(None, description="排除关键词")
    description: Optional[str] = Field(None, max_length=1000, description="主题描述")
    problem_statement: Optional[str] = Field(None, max_length=2000, description="问题陈述")
    is_active: Optional[bool] = Field(None, description="是否启用")


class TopicResponse(BaseModel):
    """研究主题响应"""
    id: uuid.UUID = Field(..., description="主题ID")
    name: str = Field(..., description="主题名称", examples=["LLM Agent"])
    keywords: list[str] = Field(..., description="关键词列表", examples=[["LLM", "agent", "tool use"]])
    exclude_keywords: list[str] = Field(default_factory=list, description="排除关键词")
    description: Optional[str] = Field(None, description="主题描述")
    problem_statement: Optional[str] = Field(None, description="问题陈述")
    is_active: bool = Field(..., description="是否启用", examples=[True])
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}
