"""通知分发服务

支持站内通知和可选的邮件通知。
"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class NotificationType(str, Enum):
    """通知类型"""
    INFO = "info"           # 普通信息
    SUCCESS = "success"     # 成功通知
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    PAPER = "paper"         # 论文相关
    SYSTEM = "system"       # 系统通知


class Notification:
    """通知对象"""

    def __init__(
        self,
        title: str,
        content: str,
        notification_type: NotificationType = NotificationType.INFO,
        user_id: str = None,
    ):
        self.id = str(uuid4())
        self.title = title
        self.content = content
        self.type = notification_type
        self.user_id = user_id
        self.is_read = False
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "type": self.type.value,
            "user_id": self.user_id,
            "is_read": self.is_read,
            "created_at": self.created_at,
        }


class NotificationDispatcher:
    """通知分发器：管理站内通知和可选的邮件通知"""

    def __init__(self, enable_email: bool = False):
        """初始化通知分发器

        Args:
            enable_email: 是否启用邮件通知
        """
        self.enable_email = enable_email
        # 站内通知存储: {user_id: [Notification, ...]}
        self._notifications: dict[str, list[Notification]] = {}
        # 邮件发送回调（需要外部注入）
        self._email_sender = None

    async def dispatch(
        self,
        title: str,
        content: str,
        user_id: str,
        notification_type: NotificationType = NotificationType.INFO,
        send_email: bool = False,
    ) -> Notification:
        """分发通知

        Args:
            title: 通知标题
            content: 通知内容
            user_id: 目标用户 ID
            notification_type: 通知类型
            send_email: 是否同时发送邮件

        Returns:
            创建的通知对象
        """
        # 创建站内通知
        notification = Notification(
            title=title,
            content=content,
            notification_type=notification_type,
            user_id=user_id,
        )

        # 存储站内通知
        if user_id not in self._notifications:
            self._notifications[user_id] = []
        self._notifications[user_id].append(notification)

        # 可选：发送邮件通知
        if send_email and self.enable_email and self._email_sender:
            await self._send_email(user_id, title, content)

        return notification

    async def dispatch_paper_notification(
        self, user_id: str, paper_title: str, message: str
    ) -> Notification:
        """发送论文相关通知

        Args:
            user_id: 用户 ID
            paper_title: 论文标题
            message: 通知消息

        Returns:
            通知对象
        """
        return await self.dispatch(
            title=f"论文通知: {paper_title[:50]}",
            content=message,
            user_id=user_id,
            notification_type=NotificationType.PAPER,
        )

    def get_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict]:
        """获取用户的通知列表

        Args:
            user_id: 用户 ID
            unread_only: 是否只返回未读通知
            limit: 最大返回数量

        Returns:
            通知字典列表
        """
        notifications = self._notifications.get(user_id, [])

        if unread_only:
            notifications = [n for n in notifications if not n.is_read]

        # 按时间倒序，返回最新通知
        notifications.sort(key=lambda n: n.created_at, reverse=True)
        return [n.to_dict() for n in notifications[:limit]]

    def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        """标记通知为已读

        Args:
            user_id: 用户 ID
            notification_id: 通知 ID

        Returns:
            是否成功标记
        """
        notifications = self._notifications.get(user_id, [])
        for n in notifications:
            if n.id == notification_id:
                n.is_read = True
                return True
        return False

    def mark_all_as_read(self, user_id: str) -> int:
        """标记用户所有通知为已读

        Args:
            user_id: 用户 ID

        Returns:
            标记的通知数量
        """
        notifications = self._notifications.get(user_id, [])
        count = 0
        for n in notifications:
            if not n.is_read:
                n.is_read = True
                count += 1
        return count

    def delete_notification(self, user_id: str, notification_id: str) -> bool:
        """删除通知

        Args:
            user_id: 用户 ID
            notification_id: 通知 ID

        Returns:
            是否成功删除
        """
        notifications = self._notifications.get(user_id, [])
        for i, n in enumerate(notifications):
            if n.id == notification_id:
                notifications.pop(i)
                return True
        return False

    def get_unread_count(self, user_id: str) -> int:
        """获取未读通知数量

        Args:
            user_id: 用户 ID

        Returns:
            未读通知数量
        """
        notifications = self._notifications.get(user_id, [])
        return sum(1 for n in notifications if not n.is_read)

    def set_email_sender(self, sender):
        """设置邮件发送回调

        Args:
            sender: 异步邮件发送函数，签名 async def send(to, subject, body)
        """
        self._email_sender = sender

    async def _send_email(self, user_id: str, title: str, content: str):
        """发送邮件通知

        Args:
            user_id: 用户 ID
            title: 邮件标题
            content: 邮件内容
        """
        try:
            await self._email_sender(user_id, title, content)
        except Exception as e:
            print(f"[Notification] 邮件发送失败: {e}")
