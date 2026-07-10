"""认证路由"""

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
async def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    用户注册

    - **email**: 用户邮箱
    - **name**: 用户名
    - **password**: 密码（至少8位）
    """
    # 1. 检查邮箱是否已注册
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )

    # 2. 创建用户
    new_user = User(
        email=user_in.email,
        name=user_in.name,
        password_hash=get_password_hash(user_in.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 3. 返回用户信息
    return ResponseBase(
        success=True,
        data=UserResponse.model_validate(new_user),
        message="注册成功",
    )


@router.post("/login", response_model=ResponseBase[Token])
async def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录

    - **email**: 用户邮箱
    - **password**: 密码
    """
    # 1. 查找用户
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )

    # 2. 验证密码
    if not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )

    # 3. 生成 JWT token
    token_data = {"user_id": str(user.id), "email": user.email}
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
async def refresh_token(current_user: User = Depends(get_current_user)):
    """
    刷新访问令牌

    需要在请求头中携带有效的 JWT token
    """
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
async def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息

    需要在请求头中携带有效的 JWT token
    """
    return ResponseBase(
        success=True,
        data=UserResponse.model_validate(current_user),
        message="ok",
    )
