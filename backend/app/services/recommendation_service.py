"""推荐服务 - Supabase 版本（含多数据源爬虫）"""
import re
import uuid
import json
import logging
from datetime import datetime, timezone

from app.services.topic_service import TopicService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def _strict_keyword_match(paper: dict, keywords: list[str]) -> bool:
    """严格关键词匹配：标题/摘要至少命中一个关键词（词边界），杜绝子串误匹配"""
    text = ((paper.get('title') or '') + ' ' + (paper.get('abstract') or '')).lower()
    for kw in keywords:
        kw = kw.strip().lower()
        if not kw:
            continue
        # 中文关键词无词边界，直接子串匹配
        if re.search(r'[\u4e00-\u9fff]', kw):
            if kw in text:
                return True
        else:
            if re.search(r'\b' + re.escape(kw) + r'\b', text):
                return True
    return False


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

        # 从多个数据源抓取论文（多抓一些，去重后才有新论文）
        papers = await self._fetch_papers(unique_keywords[:5], limit=max(limit * 3, 30))
        if not papers:
            logger.info("No papers fetched from any source")
            return []

        # 严格关键词过滤：剔除标题/摘要完全不含关键词的无关论文
        before_filter = len(papers)
        papers = [p for p in papers if _strict_keyword_match(p, unique_keywords)]
        logger.info(f"Keyword filter: {before_filter} -> {len(papers)}")

        # 去重：排除已推送的论文（批量查询，避免 N+1）
        user_papers = self.db.client.select('user_papers', user_id=str(user_id))
        pushed_identifiers = set()
        if user_papers:
            pushed_paper_ids = [up['paper_id'] for up in user_papers]
            # 分批 in 查询（PostgREST URL 长度限制）
            BATCH = 50
            for i in range(0, len(pushed_paper_ids), BATCH):
                batch_ids = pushed_paper_ids[i:i + BATCH]
                stored_papers = self.db.client.select(
                    'papers', id=('in', f"({','.join(batch_ids)})"),
                )
                for paper in stored_papers:
                    pushed_identifiers.update(
                        value for value in (
                            paper.get('id'), paper.get('doi'), paper.get('url'), paper.get('title')
                        ) if value
                    )

        new_papers = []
        for p in papers:
            paper_identifiers = {
                value for value in (
                    p.get('doi'), p.get('arxiv_id'), p.get('id'), p.get('url'), p.get('title')
                ) if value
            }
            if paper_identifiers.isdisjoint(pushed_identifiers):
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
                engine.search(query=space_query, limit=limit, sources=["openalex"], sort_by="newest"),
                # arXiv 再按相关性抓一批，增加去重后的新论文数量
                engine.search(query=arxiv_query, limit=limit, sources=["arxiv"], sort_by="relevance"),
                engine.search(query=space_query, limit=limit, sources=["semantic_scholar"], sort_by="newest"),
                return_exceptions=True,
            )
            await engine.close()

            all_papers = []
            seen_titles = set()
            for result in results:
                if isinstance(result, list):
                    for p in result:
                        # 跨源标题去重
                        t = (p.get('title') or '').strip().lower()
                        if t and t in seen_titles:
                            continue
                        if t:
                            seen_titles.add(t)
                        all_papers.append(p)
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
            doi = str(paper.get('doi', '')).strip()
            existing = self.db.client.select('papers', doi=doi) if doi else []
            if not existing and paper.get('url'):
                existing = self.db.client.select('papers', url=paper['url'])
            if not existing and paper.get('title'):
                existing = self.db.client.select('papers', title=paper['title'])

            if existing:
                paper_uuid = existing[0]['id']
            else:
                paper_uuid = str(uuid.uuid4())
                # 插入论文到 papers 表
                authors = paper.get('authors', [])
                if isinstance(authors, list):
                    authors_json = authors
                else:
                    authors_json = [str(authors)]

                # DOI 为空时不传，避免 unique constraint 冲突
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

            association = self.db.client.select(
                'user_papers', user_id=str(user_id), paper_id=str(paper_uuid)
            )
            if association:
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
