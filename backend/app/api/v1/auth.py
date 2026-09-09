"""认证路由 - Supabase 版本"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.schemas.common import ResponseBase
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.api.v1.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=ResponseBase[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db=Depends(get_db)):
    """用户注册"""
    # 1. 检查邮箱是否已注册
    existing = db.client.select('users', email=user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )

    # 2. 创建用户
    user_data = {
        'id': str(uuid.uuid4()),
        'email': user_in.email,
        'name': user_in.name,
        'password_hash': get_password_hash(user_in.password),
    }
    result = db.client.insert('users', user_data)
    new_user = result[0]

    # 3. 返回用户信息
    return ResponseBase(
        success=True,
        data=UserResponse(
            id=new_user['id'],
            email=new_user['email'],
            name=new_user['name'],
            avatar_url=new_user.get('avatar_url'),
            created_at=new_user['created_at'],
        ),
        message="注册成功",
    )


@router.post("/login", response_model=ResponseBase[Token])
async def login(user_in: UserLogin, db=Depends(get_db)):
    """用户登录"""
    # 1. 查找用户
    users = db.client.select('users', email=user_in.email)
    if not users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )
    user = users[0]

    # 2. 验证密码
    if not verify_password(user_in.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )

    # 3. 生成 JWT token
    token_data = {"user_id": user['id'], "email": user['email']}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return ResponseBase(
        success=True,
        data=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        ),
        message="登录成功",
    )


@router.post("/refresh", response_model=ResponseBase[Token])
async def refresh_token(current_user=Depends(get_current_user)):
    """刷新访问令牌"""
    token_data = {"user_id": str(current_user.id), "email": current_user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return ResponseBase(
        success=True,
        data=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        ),
        message="Token刷新成功",
    )


@router.get("/me", response_model=ResponseBase[UserResponse])
async def get_me(current_user=Depends(get_current_user)):
    """获取当前用户信息"""
    return ResponseBase(
        success=True,
        data=UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            name=current_user.name,
            avatar_url=getattr(current_user, 'avatar_url', None),
            created_at=str(current_user.created_at),
        ),
        message="ok",
    )
