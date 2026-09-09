"""推荐服务 - Supabase 版本"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.services.topic_service import TopicService
from app.services.notification_service import NotificationService


class RecommendationService:
    """推荐服务"""

    def __init__(self, db):
        self.db = db
        self.topic_service = TopicService(db)
        self.notification_service = NotificationService(db)

    def get_recommendations_for_user(self, user_id, limit: int = 10) -> list[dict]:
        """获取用户的推荐论文"""
        # Get user's topics
        topics = self.topic_service.get_topics_by_user(user_id)
        if not topics:
            return []

        # Collect all keywords from topics
        all_keywords = []
        for topic in topics:
            keywords = topic.get('keywords', [])
            if isinstance(keywords, str):
                try:
                    import json
                    keywords = json.loads(keywords)
                except:
                    keywords = []
            all_keywords.extend(keywords)

        if not all_keywords:
            return []

        # Search papers
        or_conditions = []
        for kw in all_keywords[:10]:  # Limit to avoid too long query
            or_conditions.append(f'title.ilike.%{kw}%')
            or_conditions.append(f'abstract.ilike.%{kw}%')

        papers = self.db.client.select_or('papers', or_filters=','.join(or_conditions), order='published_at.desc', limit=limit)

        # Filter out papers already pushed to user
        user_papers = self.db.client.select('user_papers', user_id=str(user_id))
        pushed_ids = {up['paper_id'] for up in user_papers}

        result = []
        for paper in papers:
            if paper['id'] not in pushed_ids:
                result.append(paper)

        return result[:limit]

    def push_papers_to_user(self, user_id, papers: list[dict]) -> int:
        """推送论文给用户"""
        count = 0
        for paper in papers:
            # Check if paper exists
            existing_papers = self.db.client.select('papers', id=paper['id'])
            if not existing_papers:
                # Create paper
                paper_data = {
                    'id': paper['id'],
                    'title': paper.get('title', ''),
                    'authors': paper.get('authors', []),
                    'abstract': paper.get('abstract', ''),
                    'source': paper.get('source', ''),
                    'url': paper.get('url', ''),
                    'doi': paper.get('doi'),
                    'published_at': paper.get('published_at'),
                }
                self.db.client.insert('papers', paper_data)

            # Create user_paper association
            data = {
                'id': str(uuid.uuid4()),
                'user_id': str(user_id),
                'paper_id': paper['id'],
                'is_bookmarked': False,
                'is_read': False,
                'pushed_at': datetime.now(timezone.utc).isoformat(),
            }
            try:
                self.db.client.insert('user_papers', data)
                count += 1
            except Exception as e:
                # Duplicate key error, skip
                pass

        return count
