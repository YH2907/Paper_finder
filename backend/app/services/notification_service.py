"""通知服务 - 数据库版本

管理通知的创建、查询、标记已读等操作。
"""

import uuid
from typing import Optional

from sqlalchemy import select, desc, func, update

from app.models.notification import Notification


class NotificationService:
    """通知服务：管理通知的 CRUD 操作"""

    def __init__(self, db):
        """初始化通知服务

        Args:
            db: 数据库会话
        """
        self.db = db

    def get_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """获取用户的通知列表

        Args:
            user_id: 用户 ID
            unread_only: 是否只返回未读通知
            limit: 最大返回数量
            offset: 偏移量

        Returns:
            通知字典列表
        """
        stmt = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            stmt = stmt.where(Notification.is_read == False)

        stmt = stmt.order_by(desc(Notification.created_at)).offset(offset).limit(limit)

        result = self.db.execute(stmt).scalars().all()

        return [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "type": n.type,
                "is_read": n.is_read,
                "created_at": n.created_at,
            }
            for n in result
        ]

    def create_notification(
        self,
        user_id: uuid.UUID,
        title: str,
        content: str,
        notification_type: str = "info",
    ) -> dict:
        """创建通知

        Args:
            user_id: 用户 ID
            title: 通知标题
            content: 通知内容
            notification_type: 通知类型（info, success, warning, error, paper, system）

        Returns:
            创建的通知信息
        """
        notification = Notification(
            user_id=user_id,
            title=title,
            content=content,
            type=notification_type,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        return {
            "id": notification.id,
            "title": notification.title,
            "content": notification.content,
            "type": notification.type,
            "is_read": notification.is_read,
            "created_at": notification.created_at,
        }

    def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """标记通知为已读

        Args:
            notification_id: 通知 ID
            user_id: 用户 ID（用于权限验证）

        Returns:
            是否成功标记
        """
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        notification = self.db.execute(stmt).scalar_one_or_none()

        if not notification:
            return False

        notification.is_read = True
        self.db.commit()
        return True

    def mark_all_read(self, user_id: uuid.UUID) -> int:
        """标记用户所有未读通知为已读

        Args:
            user_id: 用户 ID

        Returns:
            标记的通知数量
        """
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        result = self.db.execute(stmt)
        self.db.commit()

        return result.rowcount

    def get_unread_count(self, user_id: uuid.UUID) -> int:
        """获取未读通知数量

        Args:
            user_id: 用户 ID

        Returns:
            未读通知数量
        """
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
        )
        result = self.db.execute(stmt).scalar()
        return result or 0

    def delete_notification(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """删除通知

        Args:
            notification_id: 通知 ID
            user_id: 用户 ID（用于权限验证）

        Returns:
            是否成功删除
        """
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        notification = self.db.execute(stmt).scalar_one_or_none()

        if not notification:
            return False

        self.db.delete(notification)
        self.db.commit()
        return True
