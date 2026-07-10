from datetime import datetime
import uuid

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """用户注册请求"""
    email: EmailStr = Field(..., description="用户邮箱", examples=["user@example.com"])
    name: str = Field(..., min_length=1, max_length=100, description="用户名", examples=["张三"])
    password: str = Field(..., min_length=8, max_length=128, description="密码", examples=["strongpassword123"])


class UserLogin(BaseModel):
    """用户登录请求"""
    email: EmailStr = Field(..., description="用户邮箱", examples=["user@example.com"])
    password: str = Field(..., description="密码", examples=["strongpassword123"])


class UserResponse(BaseModel):
    """用户信息响应"""
    id: uuid.UUID = Field(..., description="用户ID")
    email: str = Field(..., description="用户邮箱", examples=["user@example.com"])
    name: str = Field(..., description="用户名", examples=["张三"])
    avatar_url: str | None = Field(None, description="头像URL")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT Token 响应"""
    access_token: str = Field(..., description="访问令牌", examples=["eyJhbG...VCJ9..."])
    refresh_token: str | None = Field(None, description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型", examples=["bearer"])
