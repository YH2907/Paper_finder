"""论文搜索工作流服务

提供完整的论文搜索工作流：分析问题 → 生成搜索关键词 → 搜索论文 → 过滤 → 推荐。
每个步骤发送进度更新，结果保存到数据库并创建通知。
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from sqlalchemy.orm import Session

from app.models.topic import Topic
from app.models.user import User
from app.models.paper import Paper
from app.models.user_paper import UserPaper
from app.models.notification import Notification
from app.services.ai.router import AIRouter
from app.services.crawler.engine import CrawlerEngine
from app.config import settings

# 配置日志
logger = logging.getLogger("workflow")


class WorkflowStep:
    """工作流步骤标识"""

    ANALYZE = "analyze"
    GENERATE_KEYWORDS = "generate_keywords"
    SEARCH_PAPERS = "search_papers"
    FILTER_PAPERS = "filter_papers"
    RECOMMEND = "recommend"
    DONE = "done"
    ERROR = "error"


def _make_event(step: str, status: str, message: str, data: dict = None) -> dict:
    """构建 SSE 事件数据

    Args:
        step: 当前步骤名称
        status: 状态（running / completed / error）
        message: 人类可读描述
        data: 附加数据

    Returns:
        事件字典
    """
    return {
        "step": step,
        "status": status,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data or {},
    }


class WorkflowService:
    """论文搜索工作流服务

    工作流程：
    1. 分析用户问题 → 提取核心概念
    2. 生成搜索关键词 → 英文学术关键词
    3. 搜索论文 → 并发调用多个数据源
    4. 过滤论文 → 去重 + AI 相关性过滤
    5. 推荐论文 → AI 排序 + 保存到数据库 + 创建通知
    """

    def __init__(
        self,
        db: Session,
        ai_router: Optional[AIRouter] = None,
    ):
        """初始化工作流服务

        Args:
            db: 数据库会话
            ai_router: AI 路由器实例（可选）
        """
        self.db = db
        self.ai_router = ai_router

    async def run_workflow(
        self,
        user_id: uuid.UUID,
        query: str,
        topic_id: Optional[str] = None,
        limit: int = 10,
    ) -> AsyncGenerator[str, None]:
        """执行完整的论文搜索工作流（SSE 流式）

        每个步骤完成后向客户端推送进度更新，最终推送推荐结果。

        Args:
            user_id: 用户 ID
            query: 用户的研究问题
            topic_id: 关联的研究主题 ID（可选）
            limit: 返回论文数量上限

        Yields:
            SSE 格式的 JSON 事件字符串
        """
        import asyncio

        # ── 步骤 1：分析用户问题 ──
        yield self._format_event(
            _make_event(WorkflowStep.ANALYZE, "running", "🔍 正在分析您的研究问题...")
        )

        analysis = await self._analyze_query(query, topic_id, user_id)

        yield self._format_event(
            _make_event(
                WorkflowStep.ANALYZE,
                "completed",
                f"✅ 问题分析完成：{analysis.get('summary', '')}",
                data={"analysis": analysis},
            )
        )

        # ── 步骤 2：生成搜索关键词 ──
        yield self._format_event(
            _make_event(
                WorkflowStep.GENERATE_KEYWORDS,
                "running",
                "🔑 正在生成搜索关键词...",
            )
        )

        keywords = analysis.get("search_keywords", [])
        if not keywords:
            keywords = self._extract_fallback_keywords(query)

        yield self._format_event(
            _make_event(
                WorkflowStep.GENERATE_KEYWORDS,
                "completed",
                f"✅ 已生成 {len(keywords)} 个搜索关键词",
                data={"keywords": keywords},
            )
        )

        # ── 步骤 3：搜索论文 ──
        yield self._format_event(
            _make_event(
                WorkflowStep.SEARCH_PAPERS,
                "running",
                f"📚 正在搜索论文（关键词：{', '.join(keywords[:5])}）...",
            )
        )

        raw_papers = await self._search_papers(keywords, limit=limit * 3)

        yield self._format_event(
            _make_event(
                WorkflowStep.SEARCH_PAPERS,
                "completed",
                f"✅ 搜索到 {len(raw_papers)} 篇初始论文",
                data={"total_raw": len(raw_papers)},
            )
        )

        # ── 步骤 4：过滤论文 ──
        yield self._format_event(
            _make_event(
                WorkflowStep.FILTER_PAPERS,
                "running",
                "🔧 正在过滤和去重论文...",
            )
        )

        filtered_papers = self._filter_papers(raw_papers)

        yield self._format_event(
            _make_event(
                WorkflowStep.FILTER_PAPERS,
                "completed",
                f"✅ 过滤后剩余 {len(filtered_papers)} 篇论文",
                data={"total_filtered": len(filtered_papers)},
            )
        )

        # ── 步骤 5：AI 排序推荐 ──
        yield self._format_event(
            _make_event(
                WorkflowStep.RECOMMEND,
                "running",
                "🤖 正在使用 AI 智能排序和推荐...",
            )
        )

        recommended_papers = await self._rank_and_recommend(
            query, filtered_papers, analysis, limit=limit
        )

        # ── 保存结果到数据库 ──
        saved_papers = self._save_papers(user_id, recommended_papers)

        # ── 创建通知 ──
        self._create_notification(user_id, saved_papers, analysis)

        yield self._format_event(
            _make_event(
                WorkflowStep.RECOMMEND,
                "completed",
                f"✅ 已推荐 {len(saved_papers)} 篇论文",
                data={
                    "papers": [
                        {
                            "id": str(p.paper.id) if hasattr(p, "paper") else str(p.get("id", "")),
                            "title": p.paper.title if hasattr(p, "paper") else p.get("title", ""),
                            "score": p.get("score", 0) if isinstance(p, dict) else getattr(p, "score", 0),
                        }
                        for p in saved_papers
                    ],
                },
            )
        )

        # ── 完成 ──
        yield self._format_event(
            _make_event(
                WorkflowStep.DONE,
                "completed",
                f"🎉 工作流完成！共推荐 {len(saved_papers)} 篇相关论文",
                data={"total": len(saved_papers)},
            )
        )

    # ──────────────────── 工作流内部方法 ────────────────────

    async def _analyze_query(
        self,
        query: str,
        topic_id: Optional[str],
        user_id: uuid.UUID,
    ) -> dict:
        """分析用户查询，提取关键概念和搜索关键词

        Args:
            query: 用户查询
            topic_id: 研究主题 ID
            user_id: 用户 ID

        Returns:
            分析结果字典
        """
        # 如果指定了 topic_id，获取主题信息用于上下文
        topic_context = ""
        if topic_id:
            topic = self.db.query(Topic).filter(
                Topic.id == topic_id,
                Topic.user_id == user_id,
            ).first()
            if topic:
                topic_context = (
                    f"\n研究主题：{topic.name}\n"
                    f"关键词：{', '.join(topic.keywords)}\n"
                    f"问题陈述：{topic.problem_statement or ''}"
                )

        if not self.ai_router:
            return self._default_analysis(query)

        analysis_prompt = f"""你是一个学术研究助手。请分析以下研究问题，深度理解用户的研究需求。

研究问题：
{query}
{topic_context}

请按照以下 JSON 格式回复（仅返回 JSON，无其他文字）。分析要准确、全面、有深度。
{{
  "main_concepts": ["最多5个关键概念，从抽象到具体"],
  "research_objectives": ["用户想要达到的3-4个研究目标"],
  "key_problems": ["需要解决的2-4个具体问题"],
  "search_keywords": ["7-10个精心选择的搜索关键词，包括具体技术、方法和相关领域"],
  "summary": "问题总结（一句话）"
}}"""

        try:
            messages = [{"role": "user", "content": analysis_prompt}]
            response = await self.ai_router.chat(messages)

            # 尝试解析 JSON
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return self._default_analysis(query)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"[Workflow] 分析查询失败，使用默认分析: {e}")
            return self._default_analysis(query)

    def _default_analysis(self, query: str) -> dict:
        """默认分析方法（当 AI 分析失败或不可用时）

        Args:
            query: 用户查询

        Returns:
            简单的分析结果
        """
        keywords = []
        words = query.replace("，", " ").replace("、", " ").split()
        keywords = [w for w in words if len(w) > 1][:5]

        return {
            "main_concepts": keywords[:3],
            "research_objectives": [query[:50]],
            "key_problems": [query],
            "search_keywords": keywords,
            "summary": query,
        }

    def _extract_fallback_keywords(self, query: str) -> list[str]:
        """从查询文本中提取回退关键词（当 AI 未提供时）

        Args:
            query: 查询文本

        Returns:
            关键词列表
        """
        words = query.replace("，", " ").replace("、", " ").replace("？", " ").split()
        return [w for w in words if len(w) > 1][:5]

    async def _search_papers(
        self, keywords: list[str], limit: int = 30
    ) -> list[dict]:
        """根据关键词搜索论文

        Args:
            keywords: 搜索关键词列表
            limit: 每个关键词最多搜索结果数

        Returns:
            原始论文字典列表
        """
        crawler = CrawlerEngine(ieee_api_key=settings.IEEE_API_KEY)
        all_papers = []

        try:
            for keyword in keywords[:5]:  # 最多使用 5 个关键词
                try:
                    results = await crawler.search(keyword, limit=limit)
                    all_papers.extend(results)
                    logger.info(f"[Workflow] 搜索 '{keyword}' 返回 {len(results)} 条结果")
                except Exception as e:
                    logger.error(f"[Workflow] 搜索 '{keyword}' 失败: {e}")
        finally:
            await crawler.close()

        return all_papers

    def _filter_papers(self, papers: list[dict]) -> list[dict]:
        """过滤论文：去重 + 移除无效数据

        Args:
            papers: 原始论文列表

        Returns:
            过滤后的论文列表
        """
        seen_dois = set()
        seen_titles = set()
        unique_papers = []

        for paper in papers:
            title = (paper.get("title") or "").strip()
            doi = (paper.get("doi") or "").strip()

            # 跳过没有标题的论文
            if not title:
                continue

            # 通过 DOI 去重
            if doi and doi in seen_dois:
                continue

            # 通过标题去重
            title_lower = title.lower()
            if title_lower in seen_titles:
                continue

            if doi:
                seen_dois.add(doi)
            seen_titles.add(title_lower)
            unique_papers.append(paper)

        return unique_papers

    async def _rank_and_recommend(
        self,
        query: str,
        papers: list[dict],
        analysis: dict,
        limit: int = 10,
    ) -> list[dict]:
        """使用 AI 对论文进行智能排序推荐

        Args:
            query: 原始查询
            papers: 过滤后的论文列表
            analysis: 问题分析结果
            limit: 最终推荐数量

        Returns:
            排序后的论文列表（带 score 字段）
        """
        if not papers:
            return []

        # 如果没有 AI 服务，按原始顺序返回
        if not self.ai_router:
            return [{"paper": p, "score": 0} for p in papers[:limit]]

        # 准备论文信息摘要（避免过长的 prompt）
        papers_info = []
        for i, paper in enumerate(papers[:30]):  # 最多 30 篇参与排序
            papers_info.append({
                "index": i,
                "title": paper.get("title", ""),
                "abstract": (paper.get("abstract") or "")[:300],
            })

        ranking_prompt = f"""你是一个学术研究顾问。请根据以下研究问题和论文列表，对论文进行智能排序。

重要：按照论文**能解决或回答最多关键问题**的顺序排列。

研究问题：
{query}

关键概念：
{', '.join(analysis.get('main_concepts', []))}

论文列表：
{json.dumps(papers_info, ensure_ascii=False, indent=2)}

请按照以下 JSON 格式回复（仅返回 JSON，无其他文字）：
{{
  "ranked_indices": [论文索引列表，按相关性从高到低排序],
  "scores": {{论文索引: 相关性分数 0-100}},
  "reasoning": "简要解释排序逻辑"
}}"""

        try:
            messages = [{"role": "user", "content": ranking_prompt}]
            response = await self.ai_router.chat(messages)

            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                ranking = json.loads(json_str)
                ranked_indices = ranking.get("ranked_indices", list(range(len(papers[:30]))))
                scores = ranking.get("scores", {})
            else:
                ranked_indices = list(range(min(30, len(papers))))
                scores = {}

            # 构建排序结果
            result = []
            for idx in ranked_indices[:limit]:
                if 0 <= idx < len(papers):
                    score = scores.get(str(idx), scores.get(idx, 50))
                    result.append({"paper": papers[idx], "score": score})

            return result

        except Exception as e:
            logger.error(f"[Workflow] AI 排序失败，使用默认排序: {e}")
            return [{"paper": p, "score": 50} for p in papers[:limit]]

    def _save_papers(
        self, user_id: uuid.UUID, recommended: list[dict]
    ) -> list[dict]:
        """将推荐论文保存到数据库

        Args:
            user_id: 用户 ID
            recommended: 推荐论文列表（含 paper 和 score）

        Returns:
            保存后的论文列表（含 id）
        """
        saved = []

        for item in recommended:
            raw = item.get("paper", {})
            score = item.get("score", 0)

            title = (raw.get("title") or "").strip()
            if not title:
                continue

            doi = (raw.get("doi") or "").strip()

            # 尝试查找已有论文
            existing = None
            if doi:
                existing = self.db.query(Paper).filter(Paper.doi == doi).first()
            if not existing:
                existing = self.db.query(Paper).filter(Paper.title == title).first()

            if existing:
                paper = existing
            else:
                # 创建新论文记录
                paper = Paper(
                    title=title,
                    authors=raw.get("authors", []),
                    abstract=raw.get("abstract", ""),
                    url=raw.get("url", ""),
                    doi=doi or None,
                    source=raw.get("source", "unknown"),
                )
                self.db.add(paper)
                self.db.flush()

            # 记录用户推送关联
            existing_push = (
                self.db.query(UserPaper)
                .filter(UserPaper.user_id == user_id, UserPaper.paper_id == paper.id)
                .first()
            )
            if existing_push:
                if not existing_push.pushed_at:
                    existing_push.pushed_at = datetime.now(timezone.utc)
            else:
                self.db.add(
                    UserPaper(
                        user_id=user_id,
                        paper_id=paper.id,
                        pushed_at=datetime.now(timezone.utc),
                    )
                )

            saved.append({"paper_id": paper.id, "title": title, "score": score})

        self.db.commit()
        return saved

    def _create_notification(
        self,
        user_id: uuid.UUID,
        papers: list[dict],
        analysis: dict,
    ) -> None:
        """创建推送通知

        Args:
            user_id: 用户 ID
            papers: 推荐论文列表
            analysis: 问题分析结果
        """
        if not papers:
            return

        content_lines = [f"📚 根据您的研究问题，为您推荐 {len(papers)} 篇相关论文："]

        # 显示问题分析摘要
        summary = analysis.get("summary", "")
        if summary:
            content_lines.append(f"\n📌 研究方向：{summary}")

        content_lines.append("\n论文列表：")

        for i, paper in enumerate(papers[:5], 1):
            content_lines.append(f"{i}. {paper.get('title', '未知标题')}")

        if len(papers) > 5:
            content_lines.append(f"...等共 {len(papers)} 篇论文")

        notification = Notification(
            user_id=user_id,
            title=f"🤖 工作流推荐 - {len(papers)} 篇相关论文",
            content="\n".join(content_lines),
            type="paper",
            is_read=False,
        )
        self.db.add(notification)
        self.db.commit()

        logger.info(f"[Workflow] 已为用户 {user_id} 创建推送通知，包含 {len(papers)} 篇论文")

    @staticmethod
    def _format_event(event: dict) -> str:
        """将事件字典格式化为 SSE data 行

        Args:
            event: 事件字典

        Returns:
            SSE 格式字符串
        """
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
