"""深度研究服务

分析用户的问题或文体，智能搜索并排序论文以解决问题。
"""

import json
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.topic import Topic
from app.models.paper import Paper
from app.services.ai.router import AIRouter
from app.services.paper_service import PaperService

logger = logging.getLogger("deep_research_service")


class DeepResearchService:
    """深度研究服务：分析问题 → 搜索论文 → 智能排序"""

    def __init__(
        self,
        db: Session,
        ai_router: AIRouter,
        paper_service: PaperService,
    ):
        """初始化深度研究服务

        Args:
            db: 数据库会话
            ai_router: AI 路由器
            paper_service: 论文服务
        """
        self.db = db
        self.ai_router = ai_router
        self.paper_service = paper_service

    async def deep_research(
        self,
        user_id: UUID,
        query: str,
        topic_id: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """执行深度研究

        Args:
            user_id: 用户 ID
            query: 研究问题或文体描述
            topic_id: 关联的研究主题 ID（可选）
            limit: 返回论文数量

        Returns:
            深度研究结果，包含分析和排序后的论文
        """
        try:
            # 1. 分析问题，提取关键概念和搜索关键词
            analysis = await self._analyze_query(query, topic_id, user_id)
            
            # 2. 基于关键词搜索论文
            papers = await self._search_relevant_papers(
                analysis["keywords"],
                limit=limit * 3,  # 多搜一些，便于后续排序筛选
            )

            # 3. 使用 AI 对论文进行智能排序（按解决问题的程度）
            ranked_papers = await self._rank_papers_by_relevance(
                query,
                papers,
                analysis,
                limit=limit,
            )

            return {
                "success": True,
                "analysis": analysis,
                "papers": ranked_papers,
                "total": len(ranked_papers),
                "message": f"深度研究完成，找到 {len(ranked_papers)} 篇相关论文",
            }

        except Exception as e:
            logger.error(f"深度研究失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "深度研究失败，请重试",
            }

    async def _analyze_query(
        self,
        query: str,
        topic_id: Optional[str],
        user_id: UUID,
    ) -> dict:
        """分析用户查询，提取关键概念和搜索关键词

        Args:
            query: 用户查询
            topic_id: 研究主题 ID
            user_id: 用户 ID

        Returns:
            分析结果
        """
        # 如果指定了 topic_id，获取主题信息
        topic_context = ""
        if topic_id:
            topic = self.db.query(Topic).filter(
                Topic.id == topic_id,
                Topic.user_id == user_id,
            ).first()
            if topic:
                topic_context = f"\n研究主题：{topic.name}\n关键词：{', '.join(topic.keywords)}\n问题陈述：{topic.problem_statement or ''}"

        # 使用 AI 分析问题
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
}}

例如：
{{
  "main_concepts": ["机器学习", "模型泛化", "正则化", "过拟合"],
  "research_objectives": ["理解导致过拟合的原因", "找到有效的正则化技术", "评估不同方法的效果"],
  "key_problems": ["如何检测和量化过拟合", "如何选择合适的正则化参数", "如何在不同场景应用"],
  "search_keywords": ["overfitting", "regularization", "generalization", "dropout", "weight decay", "early stopping", "cross validation", "model complexity", "bias variance tradeoff", "neural network regularization"],
  "summary": "研究如何有效解决机器学习模型的过拟合问题"
}}"""

        try:
            messages = [
                {
                    "role": "user",
                    "content": analysis_prompt,
                }
            ]
            response = await self.ai_router.chat(messages)
            
            # 尝试解析 JSON
            try:
                # 查找 JSON 对象
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    analysis = json.loads(json_str)
                else:
                    # 回退到默认分析
                    analysis = self._default_analysis(query)
            except json.JSONDecodeError:
                logger.warning("AI 返回的 JSON 格式不正确，使用默认分析")
                analysis = self._default_analysis(query)

            return analysis

        except Exception as e:
            logger.error(f"分析查询失败: {e}")
            return self._default_analysis(query)

    def _default_analysis(self, query: str) -> dict:
        """默认分析方法（当 AI 分析失败时使用）"""
        # 简单的关键词提取：按空格和标点符号分割
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

    async def _search_relevant_papers(
        self,
        keywords: list[str],
        limit: int = 50,
    ) -> list[Paper]:
        """搜索相关论文

        Args:
            keywords: 搜索关键词列表
            limit: 最多返回论文数

        Returns:
            论文列表
        """
        papers_set = {}  # 使用 dict 去重

        # 对每个关键词进行搜索
        for keyword in keywords:
            try:
                results = self.paper_service.search_papers(keyword, limit=20)
                for paper in results:
                    if paper.id not in papers_set:
                        papers_set[paper.id] = paper
                    if len(papers_set) >= limit:
                        break
            except Exception as e:
                logger.warning(f"搜索关键词 '{keyword}' 失败: {e}")
                continue

            if len(papers_set) >= limit:
                break

        return list(papers_set.values())[:limit]

    async def _rank_papers_by_relevance(
        self,
        query: str,
        papers: list[Paper],
        analysis: dict,
        limit: int = 20,
    ) -> list[dict]:
        """使用 AI 对论文进行智能排序

        按照论文对问题的解决程度排序

        Args:
            query: 原始查询
            papers: 论文列表
            analysis: 分析结果
            limit: 返回论文数

        Returns:
            排序后的论文列表
        """
        if not papers:
            return []

        # 准备论文信息
        papers_info = []
        for i, paper in enumerate(papers):
            papers_info.append({
                "index": i,
                "title": paper.title,
                "abstract": paper.abstract[:300] if paper.abstract else "",
                "authors": ", ".join(paper.authors[:3]) if paper.authors else "",
            })

        # 使用 AI 排序论文
        ranking_prompt = f"""你是一个学术研究顾问。请根据以下研究问题和论文列表，对论文进行智能排序。

重要：按照论文**能解决或回答最多关键问题**的顺序排列。最能帮助解决用户研究问题的论文应该排在前面。

研究问题：
{query}

关键概念：
{", ".join(analysis.get('main_concepts', []))}

研究目标：
{json.dumps(analysis.get('research_objectives', []), ensure_ascii=False)}

关键问题需求：
{json.dumps(analysis.get('key_problems', []), ensure_ascii=False)}

论文列表（JSON 格式）：
{json.dumps(papers_info, ensure_ascii=False, indent=2)}

请按照以下 JSON 格式回复（仅返回 JSON，无其他文字）：
{{
  "ranked_indices": [论文索引列表，按能解决问题的程度从高到低排序],
  "reasoning": "简要解释排序逻辑，特别说明前3篇论文为什么排在最前面"
}}

重要提示：
- 查看每篇论文的标题和摘要，判断其与研究问题的相关性
- 优先选择直接解决关键问题的论文
- 考虑论文的综合性和方法论的完整性
- 同时考虑不同角度的补充论文"""

        try:
            messages = [
                {
                    "role": "user",
                    "content": ranking_prompt,
                }
            ]
            response = await self.ai_router.chat(messages)
            
            # 尝试解析 JSON
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    ranking = json.loads(json_str)
                    ranked_indices = ranking.get("ranked_indices", list(range(len(papers))))
                else:
                    ranked_indices = list(range(len(papers)))
            except json.JSONDecodeError:
                logger.warning("排序 JSON 格式不正确，使用默认排序")
                ranked_indices = list(range(len(papers)))

            # 按排序顺序返回论文
            ranked_papers = []
            for idx in ranked_indices[:limit]:
                if 0 <= idx < len(papers):
                    paper = papers[idx]
                    ranked_papers.append({
                        "id": str(paper.id),
                        "title": paper.title,
                        "authors": paper.authors or [],
                        "abstract": paper.abstract,
                        "url": paper.url,
                        "source": paper.source,
                        "published_at": paper.published_at.isoformat() if paper.published_at else None,
                        "doi": paper.doi,
                    })

            return ranked_papers

        except Exception as e:
            logger.error(f"论文排序失败: {e}")
            # 回退：直接返回论文
            return [
                {
                    "id": str(paper.id),
                    "title": paper.title,
                    "authors": paper.authors or [],
                    "abstract": paper.abstract,
                    "url": paper.url,
                    "source": paper.source,
                    "published_at": paper.published_at.isoformat() if paper.published_at else None,
                    "doi": paper.doi,
                }
                for paper in papers[:limit]
            ]
