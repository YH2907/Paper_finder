"""Agent 服务 - 基于问题分析的智能论文搜索

分析用户定义的问题，生成搜索关键词，并推送相关论文。
集成工作流服务，支持完整的论文搜索工作流。
支持多数据源：arXiv、Semantic Scholar、IEEE Xplore、OpenAlex。
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.topic import Topic
from app.models.user import User
from app.models.paper import Paper
from app.models.user_paper import UserPaper
from app.models.notification import Notification
from app.services.ai.router import AIRouter
from app.services.crawler.engine import CrawlerEngine

# 配置日志
logger = logging.getLogger("agent")


class AgentService:
    """Agent 服务：基于问题分析的智能论文搜索

    核心功能：
    1. 分析用户定义的问题，生成搜索关键词
    2. 根据问题和关键词从多个数据源搜索相关论文
    3. 智能排序和推送相关论文
    4. 支持工作流模式（通过 WorkflowService）
    """

    def __init__(
        self,
        db: Session,
        ai_router: Optional[AIRouter] = None,
    ):
        """初始化 Agent 服务

        Args:
            db: 数据库会话
            ai_router: AI 路由器实例（可选，用于问题分析）
        """
        self.db = db
        self.ai_router = ai_router

    # ──────────────────── 工作流集成方法 ────────────────────

    async def run_search_workflow(
        self,
        user_id: uuid.UUID,
        query: str,
        topic_id: Optional[str] = None,
        limit: int = 10,
    ):
        """执行完整的论文搜索工作流

        委托给 WorkflowService 执行，返回 SSE 事件生成器。

        Args:
            user_id: 用户 ID
            query: 用户的研究问题
            topic_id: 关联的研究主题 ID（可选）
            limit: 返回论文数量上限
        Returns:
            SSE 事件生成器
        """
        from app.services.workflow_service import WorkflowService

        workflow = WorkflowService(db=self.db, ai_router=self.ai_router)
        return workflow.run_workflow(
            user_id=user_id,
            query=query,
            topic_id=topic_id,
            limit=limit,
        )

    # ──────────────────── 原有方法 ────────────────────

    async def analyze_problems(
        self,
        topics: list[Topic],
    ) -> list[dict]:
        """分析用户定义的问题，生成搜索关键词

        对于每个有 problem_statement 的主题，使用 AI 分析问题并生成搜索关键词。

        Args:
            topics: 用户的研究主题列表
        Returns:
            分析结果列表，每个元素包含:
            - topic_id: 主题ID
            - original_keywords: 原始关键词
            - generated_keywords: AI 生成的关键词
            - search_queries: 搜索查询列表
            - problem_analysis: 问题分析摘要
        """
        results = []

        for topic in topics:
            if not topic.problem_statement:
                # 没有问题陈述，使用原始关键词
                results.append({
                    "topic_id": topic.id,
                    "topic_name": topic.name,
                    "original_keywords": topic.keywords,
                    "generated_keywords": [],
                    "search_queries": self._build_default_queries(topic),
                    "problem_analysis": None,
                })
                continue

            # 使用 AI 分析问题
            analysis = await self._analyze_single_problem(topic)
            results.append(analysis)

        return results

    async def _analyze_single_problem(self, topic: Topic) -> dict:
        """分析单个主题的问题

        Args:
            topic: 研究主题
        Returns:
            分析结果字典
        """
        if not self.ai_router:
            # 没有 AI 服务，使用简单的关键词提取
            return {
                "topic_id": topic.id,
                "topic_name": topic.name,
                "original_keywords": topic.keywords,
                "generated_keywords": [],
                "search_queries": self._build_default_queries(topic),
                "problem_analysis": None,
            }

        # 构建 prompt
        prompt = f"""你是一个学术论文搜索助手。请分析以下研究问题，并生成搜索关键词。

研究主题：{topic.name}
主题描述：{topic.description or '无'}
问题陈述：{topic.problem_statement}
现有关键词：{', '.join(topic.keywords)}

请生成：
1. 3-5个相关的搜索关键词（英文，用于搜索学术论文）
2. 2-3个搜索查询（组合关键词，用于直接搜索）
3. 简要分析这个问题的核心要点（1-2句话）

请用 JSON 格式返回，格式如下：
{{
    "generated_keywords": ["keyword1", "keyword2", ...],
    "search_queries": ["query1", "query2", ...],
    "problem_analysis": "简要分析..."
}}"""

        try:
            messages = [
                {"role": "system", "content": "你是一个学术论文搜索助手，擅长分析研究问题并生成有效的搜索关键词。"},
                {"role": "user", "content": prompt},
            ]

            response = await self.ai_router.chat(messages)

            # 解析 JSON 响应
            # 尝试从响应中提取 JSON
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)

                return {
                    "topic_id": topic.id,
                    "topic_name": topic.name,
                    "original_keywords": topic.keywords,
                    "generated_keywords": result.get("generated_keywords", []),
                    "search_queries": result.get("search_queries", []),
                    "problem_analysis": result.get("problem_analysis"),
                }
            else:
                logger.warning(f"[Agent] AI 响应解析失败: {response[:200]}")
                return {
                    "topic_id": topic.id,
                    "topic_name": topic.name,
                    "original_keywords": topic.keywords,
                    "generated_keywords": [],
                    "search_queries": self._build_default_queries(topic),
                    "problem_analysis": None,
                }

        except Exception as e:
            logger.error(f"[Agent] 问题分析失败: {e}")
            return {
                "topic_id": topic.id,
                "topic_name": topic.name,
                "original_keywords": topic.keywords,
                "generated_keywords": [],
                "search_queries": self._build_default_queries(topic),
                "problem_analysis": None,
            }

    def _build_default_queries(self, topic: Topic) -> list[str]:
        """构建默认搜索查询（当 AI 不可用时）

        Args:
            topic: 研究主题
        Returns:
            搜索查询列表
        """
        queries = []

        # 使用问题陈述中的关键句作为查询（适配"多个问题"场景）
        problem_queries = self._extract_problem_queries(topic.problem_statement)
        queries.extend(problem_queries[:2])

        # 使用原始关键词组合
        if topic.keywords:
            # 组合前3个关键词
            queries.append(" ".join(topic.keywords[:3]))

            # 如果有更多关键词，添加单个关键词查询
            if len(topic.keywords) > 1:
                queries.append(topic.keywords[0])

        # 如果有主题名称，添加主题名称查询
        if topic.name:
            queries.append(topic.name)

        deduped: list[str] = []
        seen = set()
        for q in queries:
            qn = q.strip()
            if qn and qn not in seen:
                seen.add(qn)
                deduped.append(qn)

        return deduped[:4]

    @staticmethod
    def _extract_problem_queries(problem_statement: Optional[str]) -> list[str]:
        """从问题陈述中提取最多 3 条可用于检索的查询。"""
        if not problem_statement:
            return []

        normalized = (
            problem_statement
            .replace("\n", "。")
            .replace("?", "。")
            .replace("？", "。")
            .replace(";", "。")
            .replace("；", "。")
        )
        chunks = [c.strip() for c in normalized.split("。") if c.strip()]
        return chunks[:3]

    async def search_and_push(
        self,
        user_id: uuid.UUID,
        limit: int = 10,
        sources: list[str] = None,
    ) -> list[Paper]:
        """搜索相关论文并推送

        基于用户定义的问题从多个数据源搜索论文，并创建通知推送。

        Args:
            user_id: 用户ID
            limit: 每个主题推送的论文数量
            sources: 指定的数据源列表（None 表示全部）
        Returns:
            推送结果列表
        """
        from app.services.recommendation_service import RecommendationService

        # 获取用户的活跃主题
        topics = (
            self.db.query(Topic)
            .filter(Topic.user_id == user_id, Topic.is_active == True)
            .all()
        )

        if not topics:
            logger.info(f"[Agent] 用户 {user_id} 没有活跃主题")
            return []

        # 分析问题
        analyses = await self.analyze_problems(topics)

        # 搜索论文 - 使用所有数据源
        from app.config import settings
        crawler = CrawlerEngine(ieee_api_key=settings.IEEE_API_KEY)
        all_papers = []

        try:
            # 收集所有查询
            all_queries = []
            for analysis in analyses:
                queries = analysis.get("search_queries", [])
                if queries:
                    all_queries.extend(queries[:2])  # 每个主题最多2个查询

            if not all_queries:
                logger.info(f"[Agent] 用户 {user_id} 没有有效的搜索查询")
                return []

            # 使用多查询搜索
            raw_results = await crawler.search_multi_query(
                all_queries,
                limit_per_query=limit,
                sources=sources,
            )

            logger.info(f"[Agent] 多查询搜索返回 {len(raw_results)} 条结果")
            all_papers = raw_results

        except Exception as e:
            logger.error(f"[Agent] 搜索失败: {e}")
        finally:
            await crawler.close()

        if not all_papers:
            logger.info(f"[Agent] 用户 {user_id} 没有搜索到论文")
            return []

        # 去重
        seen_titles = set()
        unique_papers = []
        for paper in all_papers:
            title = paper.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_papers.append(paper)

        # 落库并建立用户推送关联
        persisted_papers: list[Paper] = []
        for raw in unique_papers:
            paper = self._upsert_paper(raw)
            if paper:
                self._record_user_push(user_id, paper.id)
                persisted_papers.append(paper)

        papers_to_push = persisted_papers[:limit]

        # 创建通知
        self._create_push_notification(user_id, papers_to_push, analyses)

        return papers_to_push

    def _upsert_paper(self, raw: dict) -> Optional[Paper]:
        """将抓取结果写入论文表，基于 DOI 或标题去重。"""
        doi = (raw.get("doi") or "").strip()
        title = (raw.get("title") or "").strip()
        if not title:
            return None

        existing = None
        if doi:
            existing = self.db.query(Paper).filter(Paper.doi == doi).first()
        if not existing:
            existing = self.db.query(Paper).filter(Paper.title == title).first()

        if existing:
            return existing

        # 解析发布时间
        published_at = None
        pub_value = raw.get("published") or raw.get("publication_date")
        if pub_value:
            from app.services.recommendation_service import RecommendationService
            published_at = RecommendationService._parse_published_at(pub_value)
        elif raw.get("year"):
            published_at = RecommendationService._parse_published_at(raw["year"])

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
        self.db.flush()
        return paper

    def _record_user_push(self, user_id: uuid.UUID, paper_id: uuid.UUID) -> None:
        """记录用户已收到该论文推送（用于新推送标识和已读状态）。"""
        existing = (
            self.db.query(UserPaper)
            .filter(UserPaper.user_id == user_id, UserPaper.paper_id == paper_id)
            .first()
        )
        if existing:
            if not existing.pushed_at:
                existing.pushed_at = datetime.now(timezone.utc)
            return

        self.db.add(
            UserPaper(
                user_id=user_id,
                paper_id=paper_id,
                pushed_at=datetime.now(timezone.utc),
            )
        )

    def _create_push_notification(
        self,
        user_id: uuid.UUID,
        papers: list[Paper],
        analyses: list[dict],
    ) -> None:
        """创建推送通知

        Args:
            user_id: 用户ID
            papers: 论文列表
            analyses: 分析结果列表
        """
        if not papers:
            return

        # 构建通知内容
        content_lines = [f"📚 根据您的研究问题，为您推荐 {len(papers)} 篇相关论文："]

        # 按主题分组显示
        for analysis in analyses:
            if analysis.get("problem_analysis"):
                content_lines.append(f"\n📌 {analysis['topic_name']}:")
                content_lines.append(f"   {analysis['problem_analysis']}")

        content_lines.append("\n论文列表：")

        # 显示前5篇论文
        for i, paper in enumerate(papers[:5], 1):
            title = paper.title
            source = paper.source or ""
            source_label = {
                "arxiv": "arXiv",
                "semantic_scholar": "Semantic Scholar",
                "ieee": "IEEE",
                "openalex": "OpenAlex",
            }.get(source, source)
            content_lines.append(f"{i}. [{source_label}] {title}")

        if len(papers) > 5:
            content_lines.append(f"...等共 {len(papers)} 篇论文")

        # 创建通知
        notification = Notification(
            user_id=user_id,
            title=f"🎯 问题驱动推荐 - {len(papers)} 篇相关论文",
            content="\n".join(content_lines),
            type="paper",
            is_read=False,
        )
        self.db.add(notification)
        self.db.commit()

        logger.info(f"[Agent] 已为用户 {user_id} 创建推送通知，包含 {len(papers)} 篇论文")
