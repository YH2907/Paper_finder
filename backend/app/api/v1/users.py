"""用户路由 - 用户信息管理"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.common import ResponseBase
from app.schemas.user import UserResponse
from app.schemas.user_update import UserUpdate

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me", response_model=ResponseBase[UserResponse])
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息

    需要在请求头中携带有效的 JWT token
    """
    return ResponseBase(
        success=True,
        data=UserResponse.model_validate(current_user),
        message="获取用户信息成功",
    )


@router.put("/me", response_model=ResponseBase[UserResponse])
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新当前用户信息

    - **name**: 用户名（可选）
    - **avatar_url**: 头像URL（可选）

    只更新传入的字段，未传入的字段保持不变
    """
    # 获取更新数据，排除未传入的字段
    update_data = user_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未提供任何更新数据",
        )

    # 更新用户字段
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return ResponseBase(
        success=True,
        data=UserResponse.model_validate(current_user),
        message="用户信息更新成功",
    )
