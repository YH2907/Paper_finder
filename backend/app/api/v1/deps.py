"""通用依赖注入 - Supabase 版本"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db, USE_SUPABASE
from app.core.security import decode_access_token, oauth2_scheme
from app.models.user import User


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
):
    """从JWT token获取当前用户"""
    token_data = decode_access_token(token)
    
    if USE_SUPABASE:
        # Supabase: 直接查询 users 表
        users = db.client.select('users', id=str(token_data.user_id))
        if not users:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被删除",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # 返回 SupabaseModel 包装器
        from app.core.supabase_db import SupabaseModel
        return SupabaseModel(User, users[0])
    else:
        # SQLite fallback
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被删除",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user


async def get_current_active_user(
    current_user=Depends(get_current_user),
):
    """获取当前活跃用户"""
    return current_user


def get_topic_service(db=Depends(get_db)):
    """获取主题服务"""
    from app.services.topic_service import TopicService
    return TopicService(db)
