"""通用依赖注入"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token, oauth2_scheme
from app.models.user import User
from app.services.topic_service import TopicService


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从JWT token获取当前用户

    Args:
        token: 从请求头中提取的 Bearer token
        db: 数据库会话

    Returns:
        User: 当前登录的用户对象

    Raises:
        HTTPException: token无效或用户不存在
    """
    token_data = decode_access_token(token)
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被删除",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户"""
    return current_user


def get_topic_service(db: Session = Depends(get_db)) -> TopicService:
    """获取主题服务实例"""
    return TopicService(db)
