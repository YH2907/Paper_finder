"""论文服务

处理论文的增删改查、搜索、收藏、标记已读等业务逻辑。
"""

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.user_paper import UserPaper
from app.models.topic import Topic
from app.services.crawler.engine import CrawlerEngine
from app.services.ai.analyzer import PaperAnalyzer

# 配置日志
logger = logging.getLogger("paper_service")


def _clean_keyword(keyword: str) -> list[str]:
    """清理关键词，返回有效的关键词列表"""
    cleaned = re.sub(r'[，,;；、]', ' ', keyword)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if cleaned:
        if ' ' in cleaned:
            return [w for w in cleaned.split() if w]
        return [cleaned]
    return []


def _build_keyword_conditions(keywords: list[str], max_keywords: int = 15):
    """根据关键词构建数据库查询条件"""
    conditions = []
    for kw in keywords[:max_keywords]:
        cleaned_list = _clean_keyword(kw)
        for cleaned in cleaned_list:
            pattern = f"%{cleaned}%"
            conditions.append(Paper.title.ilike(pattern))
            conditions.append(Paper.abstract.ilike(pattern))
    return conditions


def _normalize_search_query(query: str) -> str:
    """标准化搜索词，统一分隔符和空白。"""
    cleaned = re.sub(r'[，,;；、]', ' ', query)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def _tokenize_search_query(query: str, max_keywords: int = 8) -> list[str]:
    """将搜索词拆分为关键词，保留顺序并去重。"""
    if not query:
        return []

    tokens: list[str] = []
    seen: set[str] = set()
    for token in query.split(' '):
        kw = token.strip()
        if not kw:
            continue
        lowered = kw.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        tokens.append(kw)
        if len(tokens) >= max_keywords:
            break

    return tokens


class PaperService:
    """论文服务"""

    NEW_PUSH_HIGHLIGHT_MINUTES = 20

    def __init__(self, db: Session, crawler_engine: CrawlerEngine = None, analyzer: PaperAnalyzer = None):
        self.db = db
        self.crawler_engine = crawler_engine
        self.analyzer = analyzer

    def search_papers(self, query: str, limit: int = 20, sources: Optional[list[str]] = None) -> list[Paper]:
        """搜索论文（支持关键词拆分和多字段过滤）

        优化：
        - 支持多关键词拆分，每个关键词独立匹配标题/摘要
        - 按发布时间降序排列（最新在前）
        - 提前返回以减少不必要的数据库查询

        Args:
            query: 搜索关键词
            limit: 返回数量
            sources: 数据源列表（暂未使用，预留扩展）
        Returns:
            匹配的论文列表
        """
        # 清理关键词，支持中英文逗号、分号分隔
        cleaned = _normalize_search_query(query)

        if not cleaned:
            return []

        # 拆分关键词，构建 OR 条件
        keywords = _tokenize_search_query(cleaned, max_keywords=8)
        if not keywords:
            return []

        conditions = []
        for kw in keywords:  # 限制关键词数量，避免查询过慢
            pattern = f"%{kw}%"
            conditions.append(Paper.title.ilike(pattern))
            conditions.append(Paper.abstract.ilike(pattern))

        if not conditions:
            return []

        # 先召回候选，再做相关度排序，提升搜索精度
        candidates = (
            self.db.query(Paper)
            .filter(or_(*conditions))
            .order_by(Paper.published_at.desc().nullslast())
            .limit(max(limit * 12, 240))
            .all()
        )

        ranked = self._rank_papers_by_relevance(candidates, keywords, cleaned)
        return ranked[:limit]

    # ── 查询 ──────────────────────────────────────────────

    def get_papers(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        topic_id: Optional[str] = None,
        search: Optional[str] = None,
        match_all: bool = False,
    ) -> dict:
        """获取论文列表（分页、筛选、按发布时间降序）"""
        # 优化：减少不必要的数据库查询
        query = self.db.query(Paper)

        if topic_id:
            # 按主题关键词筛选
            topic = self.db.query(Topic).filter(
                Topic.id == topic_id, Topic.user_id == user_id
            ).first()
            if topic and topic.keywords:
                conditions = _build_keyword_conditions(topic.keywords)
                if conditions:
                    query = query.filter(or_(*conditions))
        elif not search:
            # 没有指定 topic_id 也没有搜索词：仅返回该用户主题关键词匹配的论文
            user_topics = self.db.query(Topic).filter(
                Topic.user_id == user_id, Topic.is_active == True
            ).all()
            if not user_topics:
                return {
                    "papers": [],
                    "total": 0,
                    "page": page,
                    "per_page": per_page,
                }

            all_keywords = []
            for t in user_topics:
                all_keywords.extend(t.keywords)
            conditions = _build_keyword_conditions(all_keywords)
            if not conditions:
                return {
                    "papers": [],
                    "total": 0,
                    "page": page,
                    "per_page": per_page,
                }
            query = query.filter(or_(*conditions))

        if search:
            # 支持关键词拆分 + 相关度排序，提升搜索精确度
            cleaned = _normalize_search_query(search)
            search_keywords = _tokenize_search_query(cleaned, max_keywords=8)

            if not search_keywords:
                keyword = f"%{search}%"
                query = query.filter(
                    or_(Paper.title.ilike(keyword), Paper.abstract.ilike(keyword))
                )
            elif match_all:
                keyword_groups = []
                for kw in search_keywords:
                    pattern = f"%{kw}%"
                    keyword_groups.append(
                        or_(
                            Paper.title.ilike(pattern),
                            Paper.abstract.ilike(pattern),
                        )
                    )
                query = query.filter(and_(*keyword_groups))
            else:
                search_conditions = []
                for kw in search_keywords:
                    pattern = f"%{kw}%"
                    search_conditions.append(Paper.title.ilike(pattern))
                    search_conditions.append(Paper.abstract.ilike(pattern))
                query = query.filter(or_(*search_conditions))

            candidates = query.order_by(Paper.published_at.desc().nullslast()).limit(500).all()
            ranked = self._rank_papers_by_relevance(candidates, search_keywords, cleaned)
            total = len(ranked)
            start = (page - 1) * per_page
            papers = ranked[start:start + per_page]
        else:
            total = query.count()
            # 按发布时间降序（最新在前），NULL 放最后
            papers = query.order_by(
                Paper.published_at.desc().nullslast()
            ).offset((page - 1) * per_page).limit(per_page).all()

        return {
            "papers": papers,
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    @staticmethod
    def _contains_term(text: str, keyword: str) -> bool:
        """判断文本是否包含关键词。"""
        if not text or not keyword:
            return False

        lowered_text = text.lower()
        lowered_kw = keyword.lower()

        # 英文关键词优先按单词边界匹配，避免 "rag" 命中 "storage"
        if re.fullmatch(r"[a-z0-9_\-]+", lowered_kw):
            return re.search(rf"(?<![a-z0-9_\-]){re.escape(lowered_kw)}(?![a-z0-9_\-])", lowered_text) is not None

        return lowered_kw in lowered_text

    def _score_paper_relevance(self, paper: Paper, keywords: list[str], phrase: str) -> float:
        """计算论文与搜索词的相关度分数。"""
        title = (paper.title or "")
        abstract = (paper.abstract or "")
        authors = " ".join(paper.authors or [])

        title_lower = title.lower()
        abstract_lower = abstract.lower()
        authors_lower = authors.lower()
        phrase_lower = phrase.lower() if phrase else ""

        score = 0.0

        if phrase_lower:
            if phrase_lower in title_lower:
                score += 120
            if phrase_lower in abstract_lower:
                score += 45

        matched_terms = 0
        title_matches = 0

        for kw in keywords:
            in_title = self._contains_term(title, kw)
            in_abstract = self._contains_term(abstract, kw)
            in_authors = self._contains_term(authors, kw)

            if in_title:
                score += 38
                matched_terms += 1
                title_matches += 1
            elif in_abstract:
                score += 16
                matched_terms += 1
            elif in_authors:
                score += 8
                matched_terms += 1

        if keywords and matched_terms == len(keywords):
            score += 28
        if title_matches >= 2:
            score += 10

        # 近期论文略微加权
        if paper.published_at:
            now = datetime.now(timezone.utc)
            published_at = paper.published_at
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            days = (now - published_at).days
            if days <= 365:
                score += 6
            elif days <= 3 * 365:
                score += 3

        return score

    def _rank_papers_by_relevance(self, papers: list[Paper], keywords: list[str], phrase: str) -> list[Paper]:
        """按相关度分数排序，分数相同时按发布时间降序。"""
        if not papers:
            return []

        scored = []
        for paper in papers:
            score = self._score_paper_relevance(paper, keywords, phrase)
            published_at = paper.published_at
            if published_at and published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            published_ts = published_at.timestamp() if published_at else 0
            scored.append((score, published_ts, paper))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item[2] for item in scored]

    def get_paper(self, paper_id: uuid.UUID) -> Optional[Paper]:
        return self.db.query(Paper).filter(Paper.id == paper_id).first()

    def get_user_paper_statuses(self, user_id: uuid.UUID, paper_ids: list[uuid.UUID]) -> dict:
        """批量获取用户-论文状态（收藏、已读）"""
        if not paper_ids:
            return {}

        user_papers = (
            self.db.query(UserPaper)
            .filter(UserPaper.user_id == user_id, UserPaper.paper_id.in_(paper_ids))
            .all()
        )

        statuses = {}
        now = datetime.now(timezone.utc)
        recent_window = timedelta(minutes=self.NEW_PUSH_HIGHLIGHT_MINUTES)

        for up in user_papers:
            is_new = False
            if up.pushed_at and not up.is_read:
                pushed_at = up.pushed_at
                if pushed_at.tzinfo is None:
                    pushed_at = pushed_at.replace(tzinfo=timezone.utc)
                is_new = now - pushed_at <= recent_window

            statuses[up.paper_id] = {
                "is_bookmarked": up.is_bookmarked,
                "is_read": up.is_read,
                "is_new": is_new,
            }

        for paper_id in paper_ids:
            if paper_id not in statuses:
                statuses[paper_id] = {"is_bookmarked": False, "is_read": False, "is_new": False}

        return statuses


    async def search_online(self, query: str, limit: int = 10, sources: Optional[list[str]] = None) -> list[Paper]:
        if not self.crawler_engine:
            return []
        raw_papers = await self.crawler_engine.search(query, limit=limit, sources=sources)
        stored_papers = []
        for raw in raw_papers:
            paper = self._upsert_paper(raw)
            if paper:
                stored_papers.append(paper)
        return stored_papers

    # ── 用户论文关联 ──────────────────────────────────────

    def bookmark_paper(self, user_id: uuid.UUID, paper_id: uuid.UUID) -> UserPaper:
        paper = self.get_paper(paper_id)
        if not paper:
            raise ValueError("论文不存在")
        user_paper = self._get_or_create_user_paper(user_id, paper_id)
        user_paper.is_bookmarked = True
        self.db.commit()
        self.db.refresh(user_paper)
        return user_paper

    def unbookmark_paper(self, user_id: uuid.UUID, paper_id: uuid.UUID) -> None:
        user_paper = (
            self.db.query(UserPaper)
            .filter(UserPaper.user_id == user_id, UserPaper.paper_id == paper_id)
            .first()
        )
        if not user_paper:
            raise ValueError("未收藏该论文")
        user_paper.is_bookmarked = False
        self.db.commit()

    def mark_read(self, user_id: uuid.UUID, paper_id: uuid.UUID) -> UserPaper:
        paper = self.get_paper(paper_id)
        if not paper:
            raise ValueError("论文不存在")
        user_paper = self._get_or_create_user_paper(user_id, paper_id)
        user_paper.is_read = True
        self.db.commit()
        self.db.refresh(user_paper)
        return user_paper

    # ── 推荐 ──────────────────────────────────────────────

    def get_bookmarked_papers(self, user_id: uuid.UUID, page: int = 1, per_page: int = 20) -> dict:
        query = (
            self.db.query(Paper)
            .join(UserPaper, UserPaper.paper_id == Paper.id)
            .filter(UserPaper.user_id == user_id, UserPaper.is_bookmarked == True)
        )
        total = query.count()
        papers = query.order_by(Paper.published_at.desc().nullslast()).offset((page - 1) * per_page).limit(per_page).all()
        return {"papers": papers, "total": total, "page": page, "per_page": per_page}

    async def get_recommendations(
        self, user_id: uuid.UUID, limit: int = 10, force_online: bool = False, only_unseen: bool = False,
        clear_history: bool = False,
    ) -> list[Paper]:
        logger.info(f"[论文服务] 获取推荐: user={user_id}, limit={limit}, force_online={force_online}")

        if self.crawler_engine:
            from app.services.recommendation_service import RecommendationService
            rec_service = RecommendationService(db=self.db, crawler_engine=self.crawler_engine, analyzer=self.analyzer)
            result = await rec_service.fetch_and_recommend(user_id=user_id, limit=limit, force_online=force_online, only_unseen=only_unseen, clear_history=clear_history)
            logger.info(f"[论文服务] 推荐服务返回 {len(result)} 篇论文")
            return result

        logger.info("[论文服务] 无爬虫引擎，使用本地搜索")
        return await self._get_recommendations_local(user_id, limit, only_unseen=only_unseen)

    async def _get_recommendations_local(self, user_id: uuid.UUID, limit: int = 10, only_unseen: bool = False) -> list[Paper]:
        topics = self.db.query(Topic).filter(Topic.user_id == user_id, Topic.is_active == True).all()
        if not topics:
            return []
        all_keywords = []
        for topic in topics:
            all_keywords.extend(topic.keywords)
        if not all_keywords:
            return []
        conditions = _build_keyword_conditions(all_keywords)
        if not conditions:
            return []
        papers = self.db.query(Paper).filter(or_(*conditions)).order_by(Paper.published_at.desc().nullslast()).limit(limit).all()
        return self._filter_unseen_local(user_id, papers)[:limit] if only_unseen else papers

    def _filter_unseen_local(self, user_id: uuid.UUID, papers: list[Paper]) -> list[Paper]:
        if not papers:
            return []
        paper_ids = [paper.id for paper in papers]
        seen_rows = self.db.query(UserPaper.paper_id).filter(UserPaper.user_id == user_id, UserPaper.paper_id.in_(paper_ids)).all()
        seen_ids = {row[0] for row in seen_rows}
        return [paper for paper in papers if paper.id not in seen_ids]

    async def get_recommended_papers(self, user_id: uuid.UUID, limit: int = 10) -> list[Paper]:
        return await self.get_recommendations(user_id, limit)

    # ── 内部方法 ──────────────────────────────────────────

    def _upsert_paper(self, raw: dict) -> Optional[Paper]:
        doi = raw.get("doi", "")
        title = raw.get("title", "")
        existing = None
        if doi:
            existing = self.db.query(Paper).filter(Paper.doi == doi).first()
        if not existing and title:
            existing = self.db.query(Paper).filter(Paper.title == title).first()
        if existing:
            return existing
        published_at = self._parse_published_at(raw.get("published") or raw.get("publication_date") or raw.get("year"))
        paper = Paper(
            title=title, authors=raw.get("authors", []), abstract=raw.get("abstract", ""),
            url=raw.get("url", ""), doi=doi or None, source=raw.get("source", "unknown"),
            published_at=published_at,
        )
        self.db.add(paper)
        self.db.commit()
        self.db.refresh(paper)
        return paper

    def _get_or_create_user_paper(self, user_id: uuid.UUID, paper_id: uuid.UUID) -> UserPaper:
        user_paper = self.db.query(UserPaper).filter(UserPaper.user_id == user_id, UserPaper.paper_id == paper_id).first()
        if not user_paper:
            user_paper = UserPaper(user_id=user_id, paper_id=paper_id, pushed_at=datetime.now(timezone.utc))
            self.db.add(user_paper)
            self.db.flush()
        return user_paper

    @staticmethod
    def _parse_published_at(value) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, int):
            try:
                return datetime(value, 1, 1, tzinfo=timezone.utc)
            except (ValueError, TypeError):
                return None
        if isinstance(value, str):
            for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y"):
                try:
                    dt = datetime.strptime(value.strip(), fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except (ValueError, TypeError):
                    continue
        return None
