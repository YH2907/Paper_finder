"""安全模块 - JWT 认证与密码处理"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel

from app.config import settings

# OAuth2 token 提取
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class TokenData(BaseModel):
    """JWT Token 数据"""
    user_id: str | None = None
    email: str | None = None


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(password_bytes, salt)
    return hash_bytes.decode('utf-8')


def get_password_hash(password: str) -> str:
    """对密码进行哈希（别名）"""
    return hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        password_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """生成 JWT access token

    Args:
        data: 要编码到 token 中的数据
        expires_delta: 过期时间增量，默认为配置中的值
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# 别名
generate_access_token = create_access_token


def create_refresh_token(data: dict) -> str:
    """生成 JWT refresh token

    Args:
        data: 要编码到 token 中的数据
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# 别名
generate_refresh_token = create_refresh_token


def decode_access_token(token: str) -> TokenData:
    """解码并验证 JWT token

    Args:
        token: JWT token 字符串

    Returns:
        TokenData: 解码后的 token 数据

    Raises:
        HTTPException: token 无效或已过期
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("user_id")
        email: str | None = payload.get("email")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭据",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(user_id=user_id, email=email)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_refresh_token(token: str) -> TokenData:
    """解码并验证 refresh token。"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh" or payload.get("user_id") is None:
            raise JWTError("invalid refresh token")
        return TokenData(user_id=payload["user_id"], email=payload.get("email"))
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前用户

    Args:
        token: JWT token

    Returns:
        当前用户
    """
    from app.core.database import USE_SUPABASE, get_db
    from app.models.user import User
    
    # 解码 token
    token_data = decode_access_token(token)
    
    # 查询用户。主路由使用 app.api.v1.deps，这里保留兼容调用方。
    session = next(get_db())
    if USE_SUPABASE:
        users = session.client.select("users", id=str(token_data.user_id))
        if not users:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
        from app.core.supabase_db import SupabaseModel
        return SupabaseModel(User, users[0])

    user = session.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
