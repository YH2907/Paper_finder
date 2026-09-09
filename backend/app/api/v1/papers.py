"""论文路由 - Supabase 版本"""
import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.services.paper_service import PaperService
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers", tags=["论文"])


# ── 辅助函数 ──────────────────────────────────────────────

def _dict_to_paper_response(p: dict) -> dict:
    """将 Supabase dict 转为前端 PaperResponse 格式"""
    return {
        "id": p.get("id", ""),
        "title": p.get("title", ""),
        "authors": p.get("authors", []) if isinstance(p.get("authors"), list) else json.loads(p.get("authors", "[]")),
        "abstract": p.get("abstract", ""),
        "url": p.get("url", ""),
        "doi": p.get("doi", None),
        "source": p.get("source", "arxiv"),
        "published_at": p.get("published_at"),
        "ai_summary": p.get("ai_summary", None),
        "ai_problem_solved": p.get("ai_problem_solved", None),
        "is_bookmarked": p.get("is_bookmarked", False),
        "is_read": p.get("is_read", False),
        "is_new": p.get("is_new", False),
    }


def _get_paper_service(db=Depends(get_db)) -> PaperService:
    return PaperService(db)


def _get_rec_service(db=Depends(get_db)) -> RecommendationService:
    return RecommendationService(db)


# ── 路由 ──────────────────────────────────────────────


@router.get("/")
async def get_papers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    topic_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    match_all: bool = Query(False),
    current_user=Depends(get_current_user),
    paper_service: PaperService = Depends(_get_paper_service),
):
    """获取用户论文列表（分页）"""
    user_id = current_user.id

    # 获取用户所有论文
    all_papers = paper_service.get_papers_by_user(user_id, limit=500)

    # 搜索过滤
    if search:
        keywords = [kw.strip().lower() for kw in search.replace("，", ",").replace("；", ";").split(",") if kw.strip()]
        if keywords:
            filtered = []
            for p in all_papers:
                title = (p.get("title") or "").lower()
                abstract = (p.get("abstract") or "").lower()
                text = f"{title} {abstract}"
                if match_all:
                    if all(kw in text for kw in keywords):
                        filtered.append(p)
                else:
                    if any(kw in text for kw in keywords):
                        filtered.append(p)
            all_papers = filtered

    # 主题过滤
    if topic_id:
        # 获取主题的关键词
        from app.services.topic_service import TopicService
        topic_svc = TopicService(paper_service.db)
        topics = topic_svc.get_topics_by_user(user_id)
        topic_keywords = []
        for t in topics:
            if str(t.get("id")) == str(topic_id):
                kws = t.get("keywords", [])
                if isinstance(kws, str):
                    try:
                        kws = json.loads(kws)
                    except Exception:
                        kws = []
                topic_keywords = [k.lower() for k in kws]
                break
        if topic_keywords:
            filtered = []
            for p in all_papers:
                title = (p.get("title") or "").lower()
                abstract = (p.get("abstract") or "").lower()
                text = f"{title} {abstract}"
                if any(kw in text for kw in topic_keywords):
                    filtered.append(p)
            all_papers = filtered

    # 分页
    total = len(all_papers)
    start = (page - 1) * per_page
    end = start + per_page
    page_papers = all_papers[start:end]

    # 标记新论文（20分钟内推送的）
    now = datetime.now(timezone.utc)
    for p in page_papers:
        pushed_at = p.get("pushed_at")
        if pushed_at:
            try:
                if isinstance(pushed_at, str):
                    pushed_dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                else:
                    pushed_dt = pushed_at
                if (now - pushed_dt).total_seconds() < 1200:
                    p["is_new"] = True
            except Exception:
                pass

    return {
        "success": True,
        "data": {
            "papers": [_dict_to_paper_response(p) for p in page_papers],
            "total": total,
            "page": page,
            "per_page": per_page,
        },
    }


@router.get("/search")
async def search_papers(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    online: bool = Query(False),
    sources: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    paper_service: PaperService = Depends(_get_paper_service),
):
    """搜索论文"""
    keywords = [kw.strip() for kw in q.replace("，", ",").replace("；", ";").split(",") if kw.strip()]
    if not keywords:
        keywords = [q]

    papers = paper_service.search_papers(keywords, limit=limit)

    if online:
        try:
            from app.services.crawler.engine import CrawlerEngine
            engine = CrawlerEngine()
            source_list = [s.strip() for s in sources.split(",")] if sources else ["arxiv", "openalex"]
            online_papers = await engine.search(query=q, limit=10, sources=source_list, sort_by="newest")
            await engine.close()
            existing_titles = {(p.get("title") or "").lower() for p in papers}
            for op in online_papers:
                if (op.get("title") or "").lower() not in existing_titles:
                    papers.append(op)
        except Exception as e:
            logger.warning(f"Online search error: {e}")

    return {
        "success": True,
        "data": [_dict_to_paper_response(p) for p in papers[:limit]],
    }


@router.get("/recommended")
async def get_recommended_papers(
    limit: int = Query(10, ge=1, le=50),
    online: bool = Query(True),
    only_unseen: bool = Query(False),
    clear_history: bool = Query(False),
    current_user=Depends(get_current_user),
    rec_service: RecommendationService = Depends(_get_rec_service),
    paper_service: PaperService = Depends(_get_paper_service),
):
    """获取推荐论文（实时搜索）"""
    user_id = current_user.id

    papers = []
    if online:
        try:
            papers = await rec_service.get_recommendations_for_user(user_id, limit=limit)
        except Exception as e:
            logger.error(f"Recommendation error: {e}")

    # 如果在线搜索没有结果，从已推送的论文中返回
    if not papers:
        papers = paper_service.get_papers_by_user(user_id, limit=limit)

    # 标记新论文
    now = datetime.now(timezone.utc)
    for p in papers:
        pushed_at = p.get("pushed_at")
        if pushed_at:
            try:
                if isinstance(pushed_at, str):
                    pushed_dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                else:
                    pushed_dt = pushed_at
                if (now - pushed_dt).total_seconds() < 1200:
                    p["is_new"] = True
            except Exception:
                pass

    result = [_dict_to_paper_response(p) for p in papers[:limit]]

    # 新论文排前面
    result.sort(key=lambda x: (not x.get("is_new", False), x.get("published_at") is None))

    return {"success": True, "data": result}


@router.get("/bookmarks")
async def get_bookmarked_papers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    paper_service: PaperService = Depends(_get_paper_service),
):
    """获取收藏的论文"""
    all_papers = paper_service.get_bookmarked_papers(current_user.id, limit=500)
    total = len(all_papers)
    start = (page - 1) * per_page
    end = start + per_page
    page_papers = all_papers[start:end]

    return {
        "success": True,
        "data": {
            "papers": [_dict_to_paper_response(p) for p in page_papers],
            "total": total,
            "page": page,
            "per_page": per_page,
        },
    }


# ── 参数路径 (必须在固定路径之后) ──────────────────────────


@router.get("/{paper_id}")
async def get_paper(
    paper_id: str,
    current_user=Depends(get_current_user),
    paper_service: PaperService = Depends(_get_paper_service),
):
    """获取论文详情"""
    paper = paper_service.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    return {"success": True, "data": _dict_to_paper_response(paper)}


@router.post("/{paper_id}/bookmark", status_code=201)
async def bookmark_paper(
    paper_id: str,
    current_user=Depends(get_current_user),
    paper_service: PaperService = Depends(_get_paper_service),
):
    """收藏论文"""
    paper_service.bookmark_paper(user_id=current_user.id, paper_id=paper_id)
    return {"success": True, "message": "收藏成功"}


@router.delete("/{paper_id}/bookmark")
async def unbookmark_paper(
    paper_id: str,
    current_user=Depends(get_current_user),
    paper_service: PaperService = Depends(_get_paper_service),
):
    """取消收藏"""
    paper_service.unbookmark_paper(user_id=current_user.id, paper_id=paper_id)
    return {"success": True, "message": "取消收藏成功"}


@router.post("/{paper_id}/read")
async def mark_paper_read(
    paper_id: str,
    current_user=Depends(get_current_user),
    paper_service: PaperService = Depends(_get_paper_service),
):
    """标记论文已读"""
    paper_service.mark_as_read(user_id=current_user.id, paper_id=paper_id)
    return {"success": True, "message": "已标记为已读"}
