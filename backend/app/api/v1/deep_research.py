"""深度研究路由"""

import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.common import ResponseBase
from app.services.deep_research_service import DeepResearchService
from app.services.workflow_service import WorkflowService
from app.services.paper_service import PaperService
from app.services.crawler.engine import CrawlerEngine
from app.services.ai.analyzer import PaperAnalyzer
from app.services.ai.router import AIRouter
from app.services.ai.groq import GroqService
from app.services.ai.gemini import GeminiService
from app.services.ai.mock import MockAIService
from app.config import settings

router = APIRouter(prefix="/deep-research", tags=["深度研究"])


def _build_ai_router() -> AIRouter:
    """构建 AI 路由器"""
    if settings.has_ai_configured:
        primary = GroqService(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
        fallback = GeminiService(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    else:
        primary = MockAIService()
        fallback = MockAIService()
    return AIRouter(primary=primary, fallback=fallback)


def _build_paper_service(db: Session) -> PaperService:
    """构建论文服务"""
    crawler = CrawlerEngine(ieee_api_key=settings.IEEE_API_KEY)

    if settings.has_ai_configured:
        primary = GroqService(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
        fallback = GeminiService(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
        ai_router = AIRouter(primary=primary, fallback=fallback)
    else:
        mock_service = MockAIService()
        ai_router = AIRouter(primary=mock_service, fallback=mock_service)

    analyzer = PaperAnalyzer(ai_router=ai_router)
    return PaperService(db=db, crawler_engine=crawler, analyzer=analyzer)


def get_deep_research_service(
    db: Session = Depends(get_db),
) -> DeepResearchService:
    """获取深度研究服务实例"""
    ai_router = _build_ai_router()
    paper_service = _build_paper_service(db)
    return DeepResearchService(
        db=db,
        ai_router=ai_router,
        paper_service=paper_service,
    )


def get_workflow_service(
    db: Session = Depends(get_db),
) -> WorkflowService:
    """获取工作流服务实例"""
    ai_router = _build_ai_router()
    return WorkflowService(db=db, ai_router=ai_router)


@router.post("/", response_model=ResponseBase[dict], status_code=status.HTTP_200_OK)
async def deep_research(
    query: str = Query(..., min_length=1, max_length=1000, description="研究问题或文体描述"),
    topic_id: Optional[str] = Query(None, description="关联的研究主题 ID（可选）"),
    limit: int = Query(20, ge=1, le=50, description="返回论文数量（1-50）"),
    current_user: User = Depends(get_current_user),
    service: DeepResearchService = Depends(get_deep_research_service),
):
    """
    执行深度研究

    深度分析用户的问题或文体，搜索相关论文，并按照**能解决最多问题**的顺序排序。

    ### 功能特点：
    - **智能分析**：AI 分析问题，提取关键概念
    - **论文搜索**：基于关键概念搜索相关论文
    - **智能排序**：按论文对问题的解决程度排序

    ### 参数：
    - **query**: 研究问题或文体描述（必需）
    - **topic_id**: 关联的研究主题 ID（可选）
    - **limit**: 返回论文数量，默认 20

    ### 示例：
    ```
    POST /api/v1/deep-research/?query=如何改进深度学习模型的泛化能力&limit=10
    ```
    """
    result = await service.deep_research(
        user_id=current_user.id,
        query=query,
        topic_id=topic_id,
        limit=limit,
    )

    return ResponseBase(
        success=result.get("success", False),
        data=result,
        message=result.get("message", "深度研究失败"),
    )


@router.post("/workflow/stream")
async def workflow_stream(
    query: str = Query(..., min_length=1, max_length=1000, description="研究问题"),
    topic_id: Optional[str] = Query(None, description="关联的研究主题 ID（可选）"),
    limit: int = Query(10, ge=1, le=50, description="返回论文数量（1-50）"),
    current_user: User = Depends(get_current_user),
    workflow: WorkflowService = Depends(get_workflow_service),
):
    """
    流式执行论文搜索工作流（SSE）

    使用 Server-Sent Events (SSE) 实时推送工作流的每个步骤进度。

    ### 工作流步骤：
    1. **分析问题** 🔍 — AI 分析用户研究问题，提取核心概念
    2. **生成关键词** 🔑 — 生成英文学术搜索关键词
    3. **搜索论文** 📚 — 并发调用 arXiv、Semantic Scholar 等数据源
    4. **过滤论文** 🔧 — 去重和基础过滤
    5. **AI 推荐** 🤖 — 使用 AI 智能排序推荐
    6. **完成** 🎉 — 保存结果并创建通知

    ### SSE 事件格式：
    ```json
    {
      "step": "analyze",
      "status": "running|completed|error",
      "message": "人类可读的进度描述",
      "timestamp": "ISO 时间戳",
      "data": { ... }
    }
    ```

    ### 示例：
    ```
    POST /api/v1/deep-research/workflow/stream?query=如何改进深度学习模型的泛化能力&limit=10
    ```
    """

    async def event_generator():
        """SSE 事件生成器"""
        try:
            async for event in workflow.run_workflow(
                user_id=current_user.id,
                query=query,
                topic_id=topic_id,
                limit=limit,
            ):
                yield event
        except Exception as e:
            error_event = json.dumps(
                {
                    "step": "error",
                    "status": "error",
                    "message": f"❌ 工作流执行失败：{str(e)}",
                    "timestamp": "",
                    "data": {"error": str(e)},
                },
                ensure_ascii=False,
            )
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
