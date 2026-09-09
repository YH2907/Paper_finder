"""推送设置路由 - Supabase 版本"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.schemas.common import ResponseBase
from app.schemas.push_settings import PushSettingsResponse, PushSettingsUpdate

router = APIRouter(prefix="/settings", tags=["设置"])


async def _trigger_realtime_recommendation(user_id) -> None:
    """推送设置变更后，后台触发一次推荐。"""
    from app.services.scheduler_service import scheduler
    await scheduler.trigger_push(user_id, trigger_reason="settings-updated")


@router.get("/push", response_model=ResponseBase[PushSettingsResponse])
async def get_push_settings(
    current_user=Depends(get_current_user),
):
    """获取当前用户的推送设置"""
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
    current_user=Depends(get_current_user),
    db=Depends(get_db),
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

    # Supabase: update users table directly
    db.client.update("users", str(current_user.id), update_data)

    # Re-read the user to get latest values
    updated = db.client.select("users", id=str(current_user.id))
    user_data = updated[0] if updated else {}

    if user_data.get("push_enabled", False):
        background_tasks.add_task(_trigger_realtime_recommendation, current_user.id)

    return ResponseBase(
        success=True,
        data=PushSettingsResponse(
            push_enabled=user_data.get("push_enabled", True),
            push_frequency=user_data.get("push_frequency", "daily"),
            push_time=user_data.get("push_time", "09:00"),
            push_count=user_data.get("push_count", 10),
        ),
        message="推送设置更新成功",
    )
