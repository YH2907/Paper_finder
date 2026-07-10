"""推荐服务

基于用户主题关键词实时搜索论文，过滤不相关结果，返回高质量推荐。
支持多数据源：arXiv、Semantic Scholar、IEEE Xplore、OpenAlex。
"""
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.topic import Topic
from app.models.user_paper import UserPaper
from app.services.crawler.engine import CrawlerEngine
from app.services.ai.analyzer import PaperAnalyzer


class RecommendationService:
    """论文推荐服务

    职责：
    - 获取用户的活跃主题关键词
    - 使用 CrawlerEngine 从多个数据源实时搜索
    - 过滤不相关论文（排除关键词 + 相关性打分）
    - 存入数据库避免重复搜索
    - 返回最近的论文（优先最新）
    """

    # 推荐论文的天数范围
    RECENT_DAYS = 7

    # 在线搜索结果的宽松匹配天数（爬虫返回的论文可能日期较老）
    ONLINE_SEARCH_DAYS = 30

    # 新推送论文的高亮窗口（分钟）
    NEW_PUSH_HIGHLIGHT_MINUTES = 20

    # 在线搜索超时时间（秒）
    ONLINE_SEARCH_TIMEOUT = 15

    def __init__(
        self,
        db: Session,
        crawler_engine: CrawlerEngine,
        analyzer: Optional[PaperAnalyzer] = None,
    ):
        """初始化推荐服务

        Args:
            db: 数据库会话
            crawler_engine: 爬虫引擎实例
            analyzer: 论文分析器（可选，用于相关性判断）
        """
        self.db = db
        self.crawler_engine = crawler_engine
        self.analyzer = analyzer

    def _mark_new_papers(self, papers: list[Paper], user_id: uuid.UUID) -> list[Paper]:
        """标记新推送的论文，并按 is_new 优先排序

        新推送的论文（最近20分钟内推送且未读）排在最前面。
        Args:
            papers: 论文列表
            user_id: 用户 ID
        Returns:
            按新论文优先排序的列表
        """
        if not papers:
            return papers

        paper_ids = [p.id for p in papers]
        now = datetime.now(timezone.utc)
        recent_window = timedelta(minutes=self.NEW_PUSH_HIGHLIGHT_MINUTES)

        # 批量查询用户-论文关联状态
        user_papers = (
            self.db.query(UserPaper)
            .filter(UserPaper.user_id == user_id, UserPaper.paper_id.in_(paper_ids))
            .all()
        )
        new_ids = set()
        for up in user_papers:
            if up.pushed_at and not up.is_read:
                pushed_at = up.pushed_at
                if pushed_at.tzinfo is None:
                    pushed_at = pushed_at.replace(tzinfo=timezone.utc)
                if now - pushed_at <= recent_window:
                    new_ids.add(up.paper_id)

        # 按：新论文优先 → 发布时间降序 排序
        def sort_key(p):
            is_new_flag = p.id in new_ids
            pub = p.published_at
            if pub is None:
                pub = datetime.min.replace(tzinfo=timezone.utc)
            elif pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            # 新论文排前面（False > True，所以取反）
            return (not is_new_flag, -pub.timestamp())

        papers.sort(key=sort_key)
        return papers

    @staticmethod
    def _clean_keyword(keyword: str) -> str:
        """清理关键词，移除特殊字符

        Args:
            keyword: 原始关键词
        Returns:
            清理后的关键词
        """
        # 移除中文逗号、英文逗号、分号等
        cleaned = re.sub(r'[，,;；、]', ' ', keyword)
        # 移除多余空格
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    async def fetch_and_recommend(
        self,
        user_id: uuid.UUID,
        limit: int = 10,
        force_online: bool = False,
        only_unseen: bool = False,
        clear_history: bool = False,
        sources: list[str] = None,
    ) -> list[Paper]:
        """获取推荐论文

        流程：
        1. 获取用户的活跃主题关键词
        2. 先查本地数据库中最近 N 天匹配的论文
        3. 如果本地结果不足且启用了在线搜索，调用爬虫实时搜索
        4. 存入数据库并过滤不相关论文
        5. 返回推荐结果（优先最新论文）

        Args:
            user_id: 用户 ID
            limit: 推荐数量
            force_online: 是否强制在线搜索（即使本地有足够结果）
            only_unseen: 是否只返回该用户未推荐过的论文
            clear_history: 是否清除推荐历史
            sources: 指定的数据源列表（None 表示全部）
        """
        import logging
        logger = logging.getLogger("recommendation")
        logger.info(f"[推荐] 用户 {user_id} 请求推荐, limit={limit}, force_online={force_online}, only_unseen={only_unseen}, sources={sources}")

        # 1. 获取用户的活跃主题
        topics = (
            self.db.query(Topic)
            .filter(Topic.user_id == user_id, Topic.is_active == True)
            .all()
        )

        if not topics:
            # 严格按关键词推荐：没有活跃主题时不返回推荐
            logger.info("[推荐] 用户没有活跃主题，返回空推荐")
            return []

        # 收集关键词和排除关键词（清理特殊字符）
        all_keywords = []
        all_exclude_keywords = []
        for topic in topics:
            for kw in topic.keywords:
                cleaned = self._clean_keyword(kw)
                if cleaned:
                    # 如果清理后包含空格，拆分成多个关键词
                    if ' ' in cleaned:
                        all_keywords.extend(cleaned.split())
                    else:
                        all_keywords.append(cleaned)
            for kw in topic.exclude_keywords:
                cleaned = self._clean_keyword(kw)
                if cleaned:
                    all_exclude_keywords.append(cleaned)

        # 去重
        all_keywords = list(set(all_keywords))
        all_exclude_keywords = list(set(all_exclude_keywords))

        if not all_keywords:
            logger.info("[推荐] 主题没有有效关键词，返回空推荐")
            return []

        logger.info(f"[推荐] 关键词: {all_keywords[:5]}, 排除: {all_exclude_keywords[:3]}")

        # 清除推荐历史（刷新时使用）
        if clear_history:
            self.db.query(UserPaper).filter(
                UserPaper.user_id == user_id,
                UserPaper.pushed_at.isnot(None)
            ).delete(synchronize_session=False)
            self.db.commit()
            logger.info(f"[推荐] 已清除用户 {user_id} 的推荐历史")

        # 2. 先查本地数据库
        local_papers = await self._search_local(
            keywords=all_keywords,
            exclude_keywords=all_exclude_keywords,
            limit=limit,
            days=self.RECENT_DAYS,
        )

        logger.info(f"[推荐] 本地搜索到 {len(local_papers)} 篇论文")

        # 如果本地结果足够且不需要强制在线搜索
        if len(local_papers) >= limit and not force_online:
            logger.info("[推荐] 本地结果足够，跳过在线搜索")
            return local_papers[:limit]

        # 3. 在线搜索 - 使用所有数据源
        online_papers = []
        if self.crawler_engine and (force_online or len(local_papers) < limit):
            # 构建搜索查询
            search_queries = []
            if force_online:
                # 刷新时直接搜索最新论文
                for topic in topics:
                    for kw in topic.keywords:
                        cleaned = self._clean_keyword(kw)
                        if cleaned:
                            search_queries.append(cleaned)
                            break
                    if search_queries:
                        break
                # 如果没有有效关键词，使用第一个主题的名称
                if not search_queries and topics:
                    search_queries = [topics[0].name]
                search_queries = search_queries[:2]
            else:
                search_queries = self._build_search_queries(topics)

            logger.info(f"[推荐] 开始在线搜索, 查询: {search_queries[:3]}, 数据源: {sources or '全部'}")

            # 使用多查询搜索
            try:
                raw_results = await self.crawler_engine.search_multi_query(
                    search_queries,
                    limit_per_query=15,
                    sources=sources,
                    sort_by="submittedDate" if force_online else "relevance",
                )
                logger.info(f"[推荐] 在线搜索返回 {len(raw_results)} 条结果")

                for raw in raw_results:
                    # 计算相关性分数
                    relevance = self._calculate_relevance(raw, all_keywords, all_exclude_keywords)
                    if relevance > 0:
                        raw["_relevance_score"] = relevance
                        paper = self._upsert_paper(raw)
                        if paper:
                            online_papers.append(paper)

            except Exception as e:
                logger.error(f"[推荐] 在线搜索失败: {e}")

        logger.info(f"[推荐] 在线搜索到 {len(online_papers)} 篇论文")

        # 5. 合并结果
        all_papers = self._merge_papers(local_papers, online_papers)

        # 6. 按发布时间降序排列（最新在前）
        all_papers = self._mark_new_papers(all_papers, user_id)

        # 7. 仅保留未推送过论文（可选）
        if only_unseen:
            all_papers = self._filter_unseen_papers(user_id, all_papers)

        selected = all_papers[:limit]

        logger.info(f"[推荐] 最终返回 {len(selected)} 篇论文 (含新论文 {sum(1 for p in selected if p.id in {pp.id for pp in all_papers if pp in all_papers[:len(selected)]})})")

        # 8. 记录推荐（创建 UserPaper 关联）
        self._record_recommendations(user_id, selected)

        return selected

    def _calculate_relevance(self, paper: dict, keywords: list[str], exclude_keywords: list[str]) -> float:
        """计算论文与关键词的相关性分数

        Args:
            paper: 论文字典
            keywords: 搜索关键词列表
            exclude_keywords: 排除关键词列表
        Returns:
            相关性分数 (0-1)，0 表示不相关
        """
        title = (paper.get("title") or "").lower()
        abstract = (paper.get("abstract") or "").lower()
        text = f"{title} {abstract}"

        # 检查排除关键词
        if exclude_keywords:
            for kw in exclude_keywords:
                if kw.lower() in text:
                    return 0.0

        if not keywords:
            return 0.5  # 没有关键词时给中等分数

        score = 0.0
        matched_keywords = 0

        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in title:
                score += 0.3  # 标题匹配权重高
                matched_keywords += 1
            elif kw_lower in abstract:
                score += 0.1  # 摘要匹配权重较低
                matched_keywords += 1

        # 匹配关键词数量加分
        if matched_keywords > 0:
            score += min(matched_keywords / len(keywords), 1.0) * 0.3

        # 引用量加分（如果有）
        citation_count = paper.get("citation_count", 0)
        if citation_count:
            score += min(citation_count / 1000, 0.2)  # 最多加 0.2

        # 最近发表加分
        year = paper.get("year") or 0
        if year:
            current_year = datetime.now().year
            if year >= current_year - 1:
                score += 0.1  # 最近两年加分

        return min(score, 1.0)

    def _get_recent_papers(self, limit: int = 10) -> list[Paper]:
        """获取最近的论文（兜底）

        Args:
            limit: 返回数量
        Returns:
            最近发布的论文列表
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.RECENT_DAYS * 2)
        return (
            self.db.query(Paper)
            .filter(Paper.published_at >= cutoff)
            .order_by(Paper.published_at.desc())
            .limit(limit)
            .all()
        )

    async def _search_local(
        self,
        keywords: list[str],
        exclude_keywords: list[str],
        limit: int = 10,
        days: int = 7,
    ) -> list[Paper]:
        """从本地数据库搜索匹配的论文

        优化：减少不必要的数据库查询，使用批量条件构建。

        Args:
            keywords: 搜索关键词列表
            exclude_keywords: 排除关键词列表
            limit: 返回数量
            days: 搜索最近几天的论文
        Returns:
            匹配的论文列表
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # 构建关键词匹配条件
        conditions = []
        for keyword in keywords[:15]:  # 限制关键词数量
            kw = f"%{keyword}%"
            conditions.append(Paper.title.ilike(kw))
            conditions.append(Paper.abstract.ilike(kw))

        if not conditions:
            return []

        query = (
            self.db.query(Paper)
            .filter(
                and_(
                    or_(*conditions),
                    # 允许 published_at 为 NULL 的论文也参与匹配（避免数据丢失）
                    or_(
                        Paper.published_at >= cutoff,
                        Paper.published_at.is_(None),
                    ),
                )
            )
            .order_by(Paper.published_at.desc())
        )

        # 只多取少量用于排除过滤，减少数据库负载
        papers = query.limit(limit * 3).all()

        # 排除关键词过滤
        if exclude_keywords:
            papers = [
                p for p in papers
                if not self._matches_exclude(p, exclude_keywords)
            ]

        return papers[:limit]

    def _build_search_queries(self, topics: list[Topic]) -> list[str]:
        """根据用户主题构建搜索查询"""
        import random
        queries = []
        for topic in topics:
            if topic.keywords:
                cleaned_keywords = []
                for kw in topic.keywords[:3]:
                    cleaned = self._clean_keyword(kw)
                    if cleaned:
                        if ' ' in cleaned:
                            cleaned_keywords.extend(cleaned.split())
                        else:
                            cleaned_keywords.append(cleaned)

                if cleaned_keywords:
                    # 组合查询
                    queries.append(" ".join(cleaned_keywords[:3]))
                    # 单个关键词查询（用于刷新时获取不同结果）
                    if len(cleaned_keywords) > 1:
                        random.shuffle(cleaned_keywords)
                        queries.append(cleaned_keywords[0])
        # 随机打乱查询顺序
        random.shuffle(queries)
        return queries

    def _filter_papers(
        self,
        papers: list[Paper],
        keywords: list[str],
        exclude_keywords: list[str],
    ) -> list[Paper]:
        """过滤论文，移除不相关的结果

        过滤规则：
        1. 排除标题/摘要中包含排除关键词的论文
        2. 标题或摘要中至少匹配一个用户关键词

        Args:
            papers: 论文列表
            keywords: 相关关键词
            exclude_keywords: 排除关键词
        Returns:
            过滤后的论文列表
        """
        filtered = []
        for paper in papers:
            # 检查排除关键词
            if exclude_keywords and self._matches_exclude(paper, exclude_keywords):
                continue

            # 检查是否匹配至少一个关键词（标题或摘要）
            text = f"{paper.title} {paper.abstract}".lower()
            if any(kw.lower() in text for kw in keywords):
                filtered.append(paper)
            elif not keywords:
                # 没有关键词时不过滤
                filtered.append(paper)

        return filtered

    def _matches_exclude(self, paper: Paper, exclude_keywords: list[str]) -> bool:
        """检查论文是否匹配排除关键词

        Args:
            paper: 论文对象
            exclude_keywords: 排除关键词列表
        Returns:
            True 表示应该排除
        """
        text = f"{paper.title} {paper.abstract}".lower()
        return any(kw.lower() in text for kw in exclude_keywords)

    def _merge_papers(self, local: list[Paper], online: list[Paper]) -> list[Paper]:
        """合并本地和在线论文，去重

        Args:
            local: 本地论文列表
            online: 在线论文列表
        Returns:
            合并去重后的论文列表
        """
        seen_ids = set()
        merged = []

        for paper in local + online:
            if paper.id not in seen_ids:
                seen_ids.add(paper.id)
                merged.append(paper)

        return merged

    def _upsert_paper(self, raw: dict) -> Optional[Paper]:
        """将爬虫返回的数据插入或更新到数据库

        通过 DOI 或标题去重。

        Args:
            raw: 爬虫返回的标准化论文字典
        Returns:
            Paper 对象
        """
        doi = raw.get("doi", "")
        title = raw.get("title", "")

        # 去重
        existing = None
        if doi:
            existing = self.db.query(Paper).filter(Paper.doi == doi).first()
        if not existing and title:
            existing = self.db.query(Paper).filter(Paper.title == title).first()

        if existing:
            return existing

        # 解析发布时间
        published_at = self._parse_published_at(
            raw.get("published")
            or raw.get("publication_date")
            or raw.get("year")
        )

        paper = Paper(
            title=title,
            authors=raw.get("authors", []),
            abstract=raw.get("abstract", ""),
            url=raw.get("url", ""),
            doi=doi or None,
            source=raw.get("source", "unknown"),
            published_at=published_at,
        )
        self.db.add(paper)
        self.db.commit()
        self.db.refresh(paper)
        return paper

    def _record_recommendations(
        self, user_id: uuid.UUID, papers: list[Paper]
    ) -> None:
        """记录推荐的论文（创建 UserPaper 关联）

        Args:
            user_id: 用户 ID
            papers: 推荐的论文列表
        """
        for paper in papers:
            existing = (
                self.db.query(UserPaper)
                .filter(
                    UserPaper.user_id == user_id,
                    UserPaper.paper_id == paper.id,
                )
                .first()
            )
            if not existing:
                user_paper = UserPaper(
                    user_id=user_id,
                    paper_id=paper.id,
                    pushed_at=datetime.now(timezone.utc),
                )
                self.db.add(user_paper)

        self.db.commit()

    def _filter_unseen_papers(
        self,
        user_id: uuid.UUID,
        papers: list[Paper],
    ) -> list[Paper]:
        """仅保留用户从未收到过的论文。"""
        if not papers:
            return []

        paper_ids = [paper.id for paper in papers]
        seen_rows = (
            self.db.query(UserPaper.paper_id)
            .filter(
                UserPaper.user_id == user_id,
                UserPaper.paper_id.in_(paper_ids),
            )
            .all()
        )
        seen_ids = {row[0] for row in seen_rows}
        return [paper for paper in papers if paper.id not in seen_ids]

    @staticmethod
    def _parse_published_at(value) -> Optional[datetime]:
        """尝试将各种格式的发布时间解析为 datetime

        Args:
            value: 字符串或整数（年份）
        Returns:
            datetime 对象，解析失败返回 None
        """
        if not value:
            return None

        if isinstance(value, int):
            try:
                return datetime(value, 1, 1, tzinfo=timezone.utc)
            except (ValueError, TypeError):
                return None

        if isinstance(value, str):
            for fmt in (
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y",
            ):
                try:
                    dt = datetime.strptime(value.strip(), fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except (ValueError, TypeError):
                    continue

        return None
