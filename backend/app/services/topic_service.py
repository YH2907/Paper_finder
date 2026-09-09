"""主题服务 - Supabase 版本"""

import uuid
import json
from typing import Optional


class TopicService:
    """主题服务类"""

    def __init__(self, db):
        self.db = db

    def get_topics_by_user(self, user_id) -> list[dict]:
        """获取用户的所有主题"""
        topics = self.db.client.select('topics', user_id=str(user_id))
        # Parse JSONB fields
        for t in topics:
            if isinstance(t.get('keywords'), str):
                try:
                    t['keywords'] = json.loads(t['keywords'])
                except (json.JSONDecodeError, TypeError):
                    t['keywords'] = []
            if isinstance(t.get('exclude_keywords'), str):
                try:
                    t['exclude_keywords'] = json.loads(t['exclude_keywords'])
                except (json.JSONDecodeError, TypeError):
                    t['exclude_keywords'] = []
        return topics

    def get_topic_by_id(self, topic_id, user_id) -> Optional[dict]:
        """获取主题详情"""
        topics = self.db.client.select('topics', id=str(topic_id), user_id=str(user_id))
        if not topics:
            return None
        t = topics[0]
        if isinstance(t.get('keywords'), str):
            try:
                t['keywords'] = json.loads(t['keywords'])
            except (json.JSONDecodeError, TypeError):
                t['keywords'] = []
        if isinstance(t.get('exclude_keywords'), str):
            try:
                t['exclude_keywords'] = json.loads(t['exclude_keywords'])
            except (json.JSONDecodeError, TypeError):
                t['exclude_keywords'] = []
        return t

    def create_topic(self, user_id, name: str, keywords: list[str], exclude_keywords: list[str] = None,
                     description: str = None, problem_statement: str = None) -> dict:
        """创建主题"""
        topic_data = {
            'id': str(uuid.uuid4()),
            'user_id': str(user_id),
            'name': name,
            'keywords': keywords,
            'exclude_keywords': exclude_keywords or [],
            'is_active': True,
        }
        if description:
            topic_data['description'] = description
        if problem_statement:
            topic_data['problem_statement'] = problem_statement

        result = self.db.client.insert('topics', topic_data)
        t = result[0]
        if isinstance(t.get('keywords'), str):
            try:
                t['keywords'] = json.loads(t['keywords'])
            except (json.JSONDecodeError, TypeError):
                pass
        if isinstance(t.get('exclude_keywords'), str):
            try:
                t['exclude_keywords'] = json.loads(t['exclude_keywords'])
            except (json.JSONDecodeError, TypeError):
                pass
        return t

    def update_topic(self, topic, name=None, keywords=None, exclude_keywords=None,
                     description=None, problem_statement=None, is_active=None) -> dict:
        """更新主题"""
        update_data = {}
        if name is not None:
            update_data['name'] = name
        if keywords is not None:
            update_data['keywords'] = keywords
        if exclude_keywords is not None:
            update_data['exclude_keywords'] = exclude_keywords
        if description is not None:
            update_data['description'] = description
        if problem_statement is not None:
            update_data['problem_statement'] = problem_statement
        if is_active is not None:
            update_data['is_active'] = is_active

        if update_data:
            topic_id = topic.get('id') if isinstance(topic, dict) else str(topic.id)
            self.db.client.update('topics', update_data, id=topic_id)

        # Refresh
        topic_id = topic.get('id') if isinstance(topic, dict) else str(topic.id)
        user_id = topic.get('user_id') if isinstance(topic, dict) else str(topic.user_id)
        return self.get_topic_by_id(topic_id, user_id) or topic

    def delete_topic(self, topic):
        """删除主题"""
        topic_id = topic.get('id') if isinstance(topic, dict) else str(topic.id)
        self.db.client.delete('topics', id=str(topic_id))

    def _normalize_keywords(self, keywords: list[str]) -> set[str]:
        result = set()
        for kw in keywords or []:
            cleaned = (kw or "").strip().lower()
            if cleaned:
                result.add(cleaned)
        return result
