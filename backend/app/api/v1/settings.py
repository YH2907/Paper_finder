"""推送设置路由"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.common import ResponseBase
from app.schemas.push_settings import PushSettingsResponse, PushSettingsUpdate

router = APIRouter(prefix="/settings", tags=["设置"])


async def _trigger_realtime_recommendation(user_id) -> None:
    """推送设置变更后，后台触发一次推荐。"""
    from app.services.scheduler_service import scheduler

    await scheduler.trigger_push(user_id, trigger_reason="settings-updated")


@router.get("/push", response_model=ResponseBase[PushSettingsResponse])
async def get_push_settings(
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户的推送设置
    """
    return ResponseBase(
        success=True,
        data=PushSettingsResponse(
            push_enabled=current_user.push_enabled,
            push_frequency=current_user.push_frequency,
            push_time=current_user.push_time,
            push_count=current_user.push_count,
        ),
    )


@router.put("/push", response_model=ResponseBase[PushSettingsResponse])
async def update_push_settings(
    settings_update: PushSettingsUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新当前用户的推送设置

    - **push_enabled**: 是否启用推送
    - **push_frequency**: 推送频率（daily/weekly/monthly）
    - **push_time**: 推送时间（HH:MM 格式）
    - **push_count**: 每次推送论文数量（1-50）
    """
    update_data = settings_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未提供任何更新数据",
        )

    # 验证推送频率
    valid_frequencies = {"daily", "weekly", "monthly"}
    if "push_frequency" in update_data:
        if update_data["push_frequency"] not in valid_frequencies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的推送频率，可选值: {', '.join(valid_frequencies)}",
            )

    # 验证推送时间格式
    if "push_time" in update_data:
        try:
            parts = update_data["push_time"].split(":")
            if len(parts) != 2:
                raise ValueError
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
            update_data["push_time"] = f"{h:02d}:{m:02d}"
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的时间格式，请使用 HH:MM 格式",
            )

    # 更新字段
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    if current_user.push_enabled:
        background_tasks.add_task(_trigger_realtime_recommendation, current_user.id)

    return ResponseBase(
        success=True,
        data=PushSettingsResponse(
            push_enabled=current_user.push_enabled,
            push_frequency=current_user.push_frequency,
            push_time=current_user.push_time,
            push_count=current_user.push_count,
        ),
        message="推送设置更新成功",
    )
