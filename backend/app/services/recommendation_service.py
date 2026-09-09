"""推荐服务 - Supabase 版本（含 arxiv 爬虫）"""
import uuid
import json
import logging
from datetime import datetime, timezone

from app.services.topic_service import TopicService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class RecommendationService:
    """推荐服务：从 arxiv 抓取论文并存入 Supabase"""

    def __init__(self, db):
        self.db = db
        self.topic_service = TopicService(db)
        self.notification_service = NotificationService(db)

    async def get_recommendations_for_user(self, user_id, limit: int = 10) -> list[dict]:
        """获取用户的推荐论文（从 arxiv 实时抓取）"""
        topics = self.topic_service.get_topics_by_user(user_id)
        if not topics:
            logger.info(f"No topics for user {user_id}")
            return []

        # 收集所有关键词
        all_keywords = []
        for topic in topics:
            keywords = topic.get('keywords', [])
            if isinstance(keywords, str):
                try:
                    keywords = json.loads(keywords)
                except Exception:
                    keywords = []
            all_keywords.extend(keywords)

        if not all_keywords:
            logger.info(f"No keywords for user {user_id}")
            return []

        logger.info(f"Fetching papers for keywords: {all_keywords[:5]}")

        # 从 arxiv 抓取论文
        papers = await self._fetch_from_arxiv(all_keywords[:5], limit=limit)
        if not papers:
            logger.info(f"No papers fetched from arxiv")
            return []

        # 去重：排除已推送的论文
        user_papers = self.db.client.select('user_papers', user_id=str(user_id))
        pushed_urls = {up.get('paper_id') for up in user_papers}

        new_papers = []
        for p in papers:
            paper_key = p.get('url') or p.get('id') or p.get('title')
            if paper_key and paper_key not in pushed_urls:
                new_papers.append(p)

        logger.info(f"Found {len(new_papers)} new papers (out of {len(papers)} fetched)")
        return new_papers[:limit]

    async def _fetch_from_arxiv(self, keywords: list[str], limit: int = 10) -> list[dict]:
        """从多个学术数据库抓取论文"""
        try:
            from app.services.crawler.engine import CrawlerEngine

            engine = CrawlerEngine()
            # 用关键词组合搜索
            query = " OR ".join(keywords[:3])
            
            # 使用所有可用的数据源：arXiv, Semantic Scholar, OpenAlex, IEEE
            results = await engine.search(
                query=query,
                limit=limit,
                sources=["arxiv", "semantic_scholar", "openalex", "ieee"],
                sort_by="newest",
            )
            await engine.close()
            return results
        except Exception as e:
            logger.error(f"Paper fetch error: {e}")
            return []

    def push_papers_to_user(self, user_id, papers: list[dict]) -> int:
        """推送论文给用户（存入 Supabase）"""
        count = 0
        for paper in papers:
            paper_id = paper.get('url') or paper.get('id') or str(uuid.uuid4())

            # 检查论文是否已存在于 papers 表
            existing = self.db.client.select('papers', id=str(paper_id))
            if not existing:
                # 插入论文
                authors = paper.get('authors', [])
                if isinstance(authors, list):
                    authors_json = authors
                else:
                    authors_json = [str(authors)]

                paper_data = {
                    'id': str(paper_id),
                    'title': paper.get('title', '')[:1024],
                    'authors': authors_json,
                    'abstract': paper.get('abstract', '') or '',
                    'source': paper.get('source', 'arxiv'),
                    'url': paper.get('url', '')[:2048],
                    'doi': paper.get('doi', '') or '',
                    'published_at': paper.get('published_at') or paper.get('published') or None,
                }
                try:
                    self.db.client.insert('papers', paper_data)
                except Exception as e:
                    logger.error(f"Insert paper error: {e}")

            # 创建 user_paper 关联
            up_id = str(uuid.uuid4())
            data = {
                'id': up_id,
                'user_id': str(user_id),
                'paper_id': str(paper_id),
                'is_bookmarked': False,
                'is_read': False,
                'relevance_score': paper.get('relevance_score', 0.8),
                'pushed_at': datetime.now(timezone.utc).isoformat(),
            }
            try:
                self.db.client.insert('user_papers', data)
                count += 1
            except Exception as e:
                logger.warning(f"Insert user_paper skipped: {e}")

        return count
