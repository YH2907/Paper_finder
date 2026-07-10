"""通知路由"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.common import ResponseBase
from app.schemas.notification import NotificationResponse, NotificationCountResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["通知"])


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    """获取通知服务"""
    return NotificationService(db=db)


@router.get("/")
async def get_notifications(
    unread_only: bool = Query(False, description="是否只返回未读通知"),
    limit: int = Query(50, ge=1, le=100, description="最大返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    获取当前用户的通知列表

    返回通知列表，按创建时间倒序排列
    - **unread_only**: 是否只返回未读通知
    - **limit**: 最大返回数量
    - **offset**: 偏移量
    """
    notifications = notification_service.get_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    return ResponseBase(
        success=True,
        data=notifications,
        message="获取通知列表成功",
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    获取未读通知数量
    """
    count = notification_service.get_unread_count(user_id=current_user.id)
    return ResponseBase(
        success=True,
        data={"unread_count": count},
        message="获取未读通知数量成功",
    )


@router.put("/{notification_id}/read", status_code=status.HTTP_200_OK)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    标记单条通知为已读

    - **notification_id**: 通知ID
    """
    success = notification_service.mark_read(
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="通知不存在")
    return ResponseBase(
        success=True,
        data=None,
        message="标记通知已读成功",
    )


@router.put("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    将所有通知标记为已读

    批量标记当前用户的所有未读通知
    """
    count = notification_service.mark_all_read(user_id=current_user.id)
    return ResponseBase(
        success=True,
        data={"marked_count": count},
        message="已将所有通知标记为已读",
    )
