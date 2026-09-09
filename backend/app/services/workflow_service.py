"""工作流服务 - Supabase 版本"""
import uuid
from datetime import datetime, timezone


class WorkflowService:
    """工作流服务"""

    def __init__(self, db):
        self.db = db

    def create_workflow(self, user_id, name: str, description: str = None) -> dict:
        """创建工作流"""
        # Note: workflows table not in schema, use a simple approach
        data = {
            'id': str(uuid.uuid4()),
            'user_id': str(user_id),
            'name': name,
            'description': description,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        return data

    def get_workflows(self, user_id) -> list[dict]:
        """获取用户的工作流"""
        # Return empty list since workflows table doesn't exist
        return []
