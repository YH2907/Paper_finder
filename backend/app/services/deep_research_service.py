"""深度研究服务 - Supabase 版本"""
import uuid
from datetime import datetime, timezone
from typing import Optional


class DeepResearchService:
    """深度研究服务"""

    def __init__(self, db):
        self.db = db

    def create_research_session(self, user_id, query: str) -> dict:
        """创建研究会话"""
        data = {
            'id': str(uuid.uuid4()),
            'user_id': str(user_id),
            'query': query,
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        # Note: deep_research_sessions table not in schema, use chats instead
        chat_data = {
            'id': data['id'],
            'user_id': str(user_id),
            'title': f'深度研究: {query[:50]}',
        }
        result = self.db.client.insert('chats', chat_data)
        return {'session_id': result[0]['id'], 'status': 'pending'}

    def get_research_session(self, session_id, user_id) -> Optional[dict]:
        """获取研究会话"""
        chats = self.db.client.select('chats', id=str(session_id), user_id=str(user_id))
        if not chats:
            return None
        
        chat = chats[0]
        messages = self.db.client.select('messages', chat_id=chat['id'], order='created_at.asc')
        
        return {
            'session_id': chat['id'],
            'query': chat['title'].replace('深度研究: ', ''),
            'status': 'completed' if messages else 'pending',
            'messages': messages,
        }
