"""通知服务 - Supabase 版本"""

import uuid


class NotificationService:
    """通知服务：管理通知的 CRUD 操作"""

    def __init__(self, db):
        self.db = db

    def create_notification(self, user_id, title: str, content: str, type: str = "info") -> dict:
        """创建通知"""
        data = {
            'id': str(uuid.uuid4()),
            'user_id': str(user_id),
            'title': title,
            'content': content,
            'type': type,
            'is_read': False,
        }
        result = self.db.client.insert('notifications', data)
        return result[0]

    def get_notifications(self, user_id, unread_only: bool = False, limit: int = 50) -> list[dict]:
        """获取用户的通知"""
        filters = {'user_id': str(user_id)}
        if unread_only:
            filters['is_read'] = 'false'
        
        notifications = self.db.client.select('notifications', order='created_at.desc', limit=limit, **filters)
        return notifications

    def get_unread_count(self, user_id) -> int:
        """获取未读通知数量"""
        return self.db.client.count('notifications', user_id=str(user_id), is_read='false')

    def mark_as_read(self, notification_id, user_id) -> bool:
        """标记通知为已读"""
        # Check ownership
        existing = self.db.client.select('notifications', id=str(notification_id), user_id=str(user_id))
        if not existing:
            return False
        
        self.db.client.update('notifications', {'is_read': True}, id=str(notification_id))
        return True

    def mark_all_as_read(self, user_id) -> int:
        """标记所有通知为已读"""
        # Get unread notifications
        unread = self.db.client.select('notifications', user_id=str(user_id), is_read='false')
        count = 0
        for n in unread:
            self.db.client.update('notifications', {'is_read': True}, id=n['id'])
            count += 1
        return count

    def delete_notification(self, notification_id, user_id) -> bool:
        """删除通知"""
        existing = self.db.client.select('notifications', id=str(notification_id), user_id=str(user_id))
        if not existing:
            return False
        
        self.db.client.delete('notifications', id=str(notification_id))
        return True
