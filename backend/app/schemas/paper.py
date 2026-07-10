import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PaperResponse(BaseModel):
    """论文详情响应"""
    id: uuid.UUID = Field(..., description="论文ID")
    title: str = Field(..., description="论文标题", examples=["Attention Is All You Need"])
    authors: list[str] = Field(..., description="作者列表", examples=[["Ashish Vaswani", "Noam Shazeer"]])
    abstract: str = Field(..., description="摘要")
    url: str = Field(..., description="论文链接", examples=["https://arxiv.org/abs/1706.03762"])
    doi: Optional[str] = Field(None, description="DOI")
    source: str = Field(..., description="来源", examples=["arxiv"])
    published_at: Optional[datetime] = Field(None, description="发布时间")
    ai_summary: Optional[str] = Field(None, description="AI 生成的中文摘要")
    ai_problem_solved: Optional[str] = Field(None, description="AI 识别的论文解决的问题")
    is_bookmarked: bool = Field(False, description="当前用户是否已收藏")
    is_read: bool = Field(False, description="当前用户是否已读")
    is_new: bool = Field(False, description="是否为新推送的论文")

    model_config = {"from_attributes": True}


class PaperListResponse(BaseModel):
    """论文列表响应"""
    papers: list[PaperResponse] = Field(..., description="论文列表")
    total: int = Field(..., description="总数", examples=[100])
    page: int = Field(..., description="当前页码", examples=[1])
    per_page: int = Field(..., description="每页数量", examples=[20])
