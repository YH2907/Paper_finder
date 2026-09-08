"""论文路由"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.paper import PaperResponse, PaperListResponse
from app.schemas.common import ResponseBase
from app.services.paper_service import PaperService
from app.services.crawler.engine import CrawlerEngine
from app.services.ai.analyzer import PaperAnalyzer
from app.services.ai import build_ai_router
from app.config import settings

router = APIRouter(prefix="/papers", tags=["论文"])

# ── 依赖注入 ──────────────────────────────────────────────


def get_crawler_engine() -> CrawlerEngine:
    """获取爬虫引擎单例"""
    return CrawlerEngine(ieee_api_key=settings.IEEE_API_KEY)


def get_analyzer() -> PaperAnalyzer:
    """获取论文分析器"""
    ai_router = build_ai_router()
    return PaperAnalyzer(ai_router=ai_router)


def get_paper_service(
    db: Session = Depends(get_db),
    crawler: CrawlerEngine = Depends(get_crawler_engine),
    analyzer: PaperAnalyzer = Depends(get_analyzer),
) -> PaperService:
    """获取论文服务"""
    return PaperService(db=db, crawler_engine=crawler, analyzer=analyzer)


# ── 路由 (注意：固定路径必须在参数路径之前) ──────────────────


@router.get("/", response_model=ResponseBase[PaperListResponse])
async def get_papers(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    topic_id: Optional[str] = Query(None, description="按主题筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    match_all: bool = Query(False, description="是否要求全部关键词命中"),
    current_user: User = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service),
):
    """
    获取论文列表

    支持分页和筛选：
    - **page**: 页码（从1开始）
    - **per_page**: 每页数量（1-100）
    - **topic_id**: 按主题筛选
    - **search**: 搜索标题或摘要
    - **match_all**: 开启后要求搜索词全部命中
    """
    result = paper_service.get_papers(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        topic_id=topic_id,
        search=search,
        match_all=match_all,
    )

    # 批量获取用户论文状态
    paper_ids = [p.id for p in result["papers"]]
    statuses = paper_service.get_user_paper_statuses(current_user.id, paper_ids)

    paper_responses = []
    for p in result["papers"]:
        pr = PaperResponse.model_validate(p)
        status = statuses.get(p.id, {"is_bookmarked": False, "is_read": False, "is_new": False})
        pr.is_bookmarked = status["is_bookmarked"]
        pr.is_read = status["is_read"]
        pr.is_new = status["is_new"]
        paper_responses.append(pr)

    return ResponseBase(
        success=True,
        data=PaperListResponse(
            papers=paper_responses,
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
        ),
    )


@router.get("/search", response_model=ResponseBase[list[PaperResponse]])
async def search_papers(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    online: bool = Query(False, description="是否在线搜索爬虫数据源"),
    sources: Optional[str] = Query(None, description="数据源，逗号分隔，如 arxiv,semantic_scholar"),
    current_user: User = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service),
):
    """
    搜索论文

    - **q**: 搜索关键词（必填）
    - **limit**: 返回数量（1-100）
    - **online**: 是否同时在线搜索（调用爬虫）
    - **sources**: 指定数据源，逗号分隔
    """
    # 本地搜索（支持关键词拆分过滤）
    papers = paper_service.search_papers(query=q, limit=limit)

    # 在线搜索（可选）
    if online:
        source_list = [s.strip() for s in sources.split(",")] if sources else None
        online_papers = await paper_service.search_online(query=q, limit=10, sources=source_list)
        # 合并去重
        existing_ids = {p.id for p in papers}
        for p in online_papers:
            if p.id not in existing_ids:
                papers.append(p)

    # 按发布时间降序排列（最新在前）
    papers.sort(
        key=lambda p: p.published_at if p.published_at else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    # 批量获取用户论文状态
    limited_papers = papers[:limit]
    paper_ids = [p.id for p in limited_papers]
    statuses = paper_service.get_user_paper_statuses(current_user.id, paper_ids)

    paper_responses = []
    for p in limited_papers:
        pr = PaperResponse.model_validate(p)
        status = statuses.get(p.id, {"is_bookmarked": False, "is_read": False, "is_new": False})
        pr.is_bookmarked = status["is_bookmarked"]
        pr.is_read = status["is_read"]
        pr.is_new = status["is_new"]
        paper_responses.append(pr)

    return ResponseBase(success=True, data=paper_responses)


@router.get("/recommended", response_model=ResponseBase[list[PaperResponse]])
async def get_recommended_papers(
    limit: int = Query(10, ge=1, le=50, description="推荐数量"),
    online: bool = Query(True, description="是否在线实时搜索最新论文"),
    only_unseen: bool = Query(False, description="是否只返回未推荐过的新论文"),
    clear_history: bool = Query(False, description="是否清除推荐历史（刷新时使用）"),
    current_user: User = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service),
):
    """
    获取推荐论文（实时搜索）
    """
    papers = await paper_service.get_recommendations(
        user_id=current_user.id,
        limit=limit,
        force_online=online,
        only_unseen=only_unseen,
        clear_history=clear_history,
    )

    # 新推送的论文已在推荐服务中排在最前面
    # 批量获取用户论文状态
    paper_ids = [p.id for p in papers]
    statuses = paper_service.get_user_paper_statuses(current_user.id, paper_ids)

    paper_responses = []
    for p in papers:
        pr = PaperResponse.model_validate(p)
        status = statuses.get(p.id, {"is_bookmarked": False, "is_read": False, "is_new": False})
        pr.is_bookmarked = status["is_bookmarked"]
        pr.is_read = status["is_read"]
        pr.is_new = status["is_new"]
        paper_responses.append(pr)

    # 确保新论文排在最前面（双重保障）
    paper_responses.sort(key=lambda x: (not x.is_new, x.published_at is None, -(x.published_at.timestamp() if x.published_at else 0)))

    return ResponseBase(success=True, data=paper_responses)


@router.get("/bookmarks", response_model=ResponseBase[PaperListResponse])
async def get_bookmarked_papers(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service),
):
    """
    获取收藏的论文列表
    """
    result = paper_service.get_bookmarked_papers(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
    )
    # 收藏列表中的论文 is_bookmarked=True, 还需要查 is_read
    paper_ids = [p.id for p in result["papers"]]
    statuses = paper_service.get_user_paper_statuses(current_user.id, paper_ids)

    paper_responses = []
    for p in result["papers"]:
        pr = PaperResponse.model_validate(p)
        status = statuses.get(p.id, {"is_bookmarked": False, "is_read": False, "is_new": False})
        pr.is_bookmarked = True  # 来自收藏列表，必然是 True
        pr.is_read = status["is_read"]
        pr.is_new = status["is_new"]
        paper_responses.append(pr)

    return ResponseBase(
        success=True,
        data=PaperListResponse(
            papers=paper_responses,
            total=result["total"],
            page=result["page"],
            per_page=result["per_page"],
        ),
    )


# ── 参数路径 (必须在固定路径之后) ──────────────────────────


@router.get("/{paper_id}", response_model=ResponseBase[PaperResponse])
async def get_paper(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service),
):
    """
    获取论文详情

    - **paper_id**: 论文ID
    """
    paper = paper_service.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="论文不存在")
    pr = PaperResponse.model_validate(paper)
    statuses = paper_service.get_user_paper_statuses(current_user.id, [paper.id])
    status_data = statuses.get(paper.id, {"is_bookmarked": False, "is_read": False, "is_new": False})
    pr.is_bookmarked = status_data["is_bookmarked"]
    pr.is_read = status_data["is_read"]
    pr.is_new = status_data["is_new"]
    return ResponseBase(success=True, data=pr)


@router.post("/{paper_id}/analyze", response_model=ResponseBase[dict])
async def analyze_paper(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service),
):
    """
    AI 分析论文

    调用 AI 服务对论文进行分析，生成摘要和问题识别。
    - **paper_id**: 论文ID
    """
    paper = paper_service.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="论文不存在")

    if paper.ai_summary:
        # 已有分析结果，直接返回
        return ResponseBase(
            success=True,
            data={
                "summary": paper.ai_summary,
                "problem_solved": paper.ai_problem_solved,
                "cached": True,
            },
        )

    # 调用 AI 分析
    if paper_service.analyzer:
        analysis = await paper_service.analyzer.analyze(paper.title, paper.abstract)
        # 保存分析结果
        paper.ai_summary = analysis.get("summary", "")
        paper.ai_problem_solved = "\n".join(analysis.get("problems", []))
        paper_service.db.commit()

        return ResponseBase(
            success=True,
            data={
                **analysis,
                "cached": False,
                "mock_mode": not settings.has_ai_configured,
            },
        )

    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI 分析服务不可用")


@router.post("/{paper_id}/bookmark", status_code=status.HTTP_201_CREATED)
async def bookmark_paper(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service),
):
    """
    收藏论文

    - **paper_id**: 论文ID
    """
    try:
        paper_service.bookmark_paper(user_id=current_user.id, paper_id=paper_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ResponseBase(success=True, message="收藏成功")


@router.delete("/{paper_id}/bookmark", status_code=status.HTTP_200_OK)
async def unbookmark_paper(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service),
):
    """
    取消收藏论文

    - **paper_id**: 论文ID
    """
    try:
        paper_service.unbookmark_paper(user_id=current_user.id, paper_id=paper_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ResponseBase(success=True, message="取消收藏成功")


@router.post("/{paper_id}/read", status_code=status.HTTP_200_OK)
async def mark_paper_read(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    paper_service: PaperService = Depends(get_paper_service),
):
    """
    标记论文已读

    - **paper_id**: 论文ID
    """
    try:
        paper_service.mark_read(user_id=current_user.id, paper_id=paper_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ResponseBase(success=True, message="已标记为已读")
