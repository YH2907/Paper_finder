"""Agent 服务 - Supabase 版本"""
import uuid
from datetime import datetime, timezone


class AgentService:
    """Agent 服务"""

    def __init__(self, db):
        self.db = db

    def create_agent(self, user_id, name: str, prompt: str) -> dict:
        """创建 Agent"""
        # Note: agents table not in schema
        data = {
            'id': str(uuid.uuid4()),
            'user_id': str(user_id),
            'name': name,
            'prompt': prompt,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        return data

    def get_agents(self, user_id) -> list[dict]:
        """获取用户的 Agents"""
        # Return empty list since agents table doesn't exist
        return []
