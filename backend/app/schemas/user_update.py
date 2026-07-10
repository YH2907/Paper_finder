"""用户相关请求模型"""

from typing import Optional

from pydantic import BaseModel, Field


class UserUpdate(BaseModel):
    """用户信息更新请求"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="用户名", examples=["张三"]
    )
    avatar_url: Optional[str] = Field(None, max_length=512, description="头像URL")
