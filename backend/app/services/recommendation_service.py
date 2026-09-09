"""推荐服务 - Supabase 版本（含多数据源爬虫）"""
import uuid
import json
import logging
from datetime import datetime, timezone

from app.services.topic_service import TopicService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class RecommendationService:
    """推荐服务：从多个学术数据库抓取论文并存入 Supabase"""

    def __init__(self, db):
        self.db = db
        self.topic_service = TopicService(db)
        self.notification_service = NotificationService(db)

    async def get_recommendations_for_user(self, user_id, limit: int = 10) -> list[dict]:
        """获取用户的推荐论文（实时抓取）"""
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

        # 去重关键词
        seen = set()
        unique_keywords = []
        for kw in all_keywords:
            kw_lower = kw.strip().lower()
            if kw_lower and kw_lower not in seen:
                seen.add(kw_lower)
                unique_keywords.append(kw.strip())

        logger.info(f"Fetching papers for keywords: {unique_keywords[:5]}")

        # 从多个数据源抓取论文
        papers = await self._fetch_papers(unique_keywords[:5], limit=limit)
        if not papers:
            logger.info("No papers fetched from any source")
            return []

        # 去重：排除已推送的论文
        user_papers = self.db.client.select('user_papers', user_id=str(user_id))
        pushed_ids = {up.get('paper_id') for up in user_papers}

        new_papers = []
        for p in papers:
            paper_key = p.get('doi') or p.get('arxiv_id') or p.get('id') or p.get('title', '')[:50]
            if paper_key and paper_key not in pushed_ids:
                new_papers.append(p)

        logger.info(f"Found {len(new_papers)} new papers (out of {len(papers)} fetched)")
        return new_papers[:limit]

    async def _fetch_papers(self, keywords: list[str], limit: int = 10) -> list[dict]:
        """从多个学术数据库并发抓取论文"""
        try:
            from app.services.crawler.engine import CrawlerEngine

            engine = CrawlerEngine()
            
            # 过滤掉 OR/AND/NOT 等布尔关键词
            clean_keywords = [kw for kw in keywords if kw.upper() not in ('OR', 'AND', 'NOT')]
            if not clean_keywords:
                clean_keywords = keywords
            
            # arXiv 用 OR 连接关键词
            arxiv_query = " OR ".join(clean_keywords)
            # Semantic Scholar/OpenAlex 用空格连接
            space_query = " ".join(clean_keywords)
            
            results = await asyncio.gather(
                engine.search(query=arxiv_query, limit=limit, sources=["arxiv"], sort_by="newest"),
                engine.search(query=space_query, limit=limit, sources=["semantic_scholar"], sort_by="newest"),
                engine.search(query=space_query, limit=limit, sources=["openalex"], sort_by="newest"),
                return_exceptions=True,
            )
            await engine.close()

            all_papers = []
            for result in results:
                if isinstance(result, list):
                    all_papers.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Source error: {result}")

            logger.info(f"Total papers fetched: {len(all_papers)}")
            return all_papers
        except Exception as e:
            logger.error(f"Paper fetch error: {e}")
            return []

    def push_papers_to_user(self, user_id, papers: list[dict]) -> int:
        """推送论文给用户（存入 Supabase）"""
        count = 0
        for paper in papers:
            # 生成 UUID 作为 paper_id（papers 表 id 是 UUID 类型）
            paper_uuid = str(uuid.uuid4())
            # 用 DOI 或 arXiv ID 作为稳定标识
            stable_id = paper.get('doi') or paper.get('arxiv_id') or paper.get('id', '')

            # 检查是否已推送（通过 stable_id 去重）
            existing = self.db.client.select(
                'papers',
                doi=str(paper.get('doi', '')) if paper.get('doi') else None,
            ) if paper.get('doi') else []

            if not existing:
                # 插入论文到 papers 表
                authors = paper.get('authors', [])
                if isinstance(authors, list):
                    authors_json = authors
                else:
                    authors_json = [str(authors)]

                # DOI 为空时不传，避免 unique constraint 冲突
                doi = str(paper.get('doi', '')) or ''
                paper_data = {
                    'id': paper_uuid,
                    'title': str(paper.get('title', ''))[:1024],
                    'authors': authors_json,
                    'abstract': str(paper.get('abstract', '')) or '',
                    'source': str(paper.get('source', 'arxiv')),
                    'url': str(paper.get('url', ''))[:2048],
                    'published_at': paper.get('published_at') or paper.get('published') or None,
                }
                if doi:
                    paper_data['doi'] = doi
                try:
                    self.db.client.insert('papers', paper_data)
                except Exception as e:
                    logger.error(f"Insert paper error: {e}")
                    continue

            # 创建 user_papers 关联
            up_id = str(uuid.uuid4())
            data = {
                'id': up_id,
                'user_id': str(user_id),
                'paper_id': paper_uuid,
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


import asyncio
