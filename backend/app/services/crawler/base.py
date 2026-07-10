"""爬虫基类"""

from abc import ABC, abstractmethod
from typing import Optional

import httpx


class BaseCrawler(ABC):
    """爬虫基类"""

    def __init__(self, rate_limit: float = 1.0):
        # 请求速率限制（秒）
        self.rate_limit = rate_limit
        # 异步 HTTP 客户端
        self.client = httpx.AsyncClient(timeout=30.0)

    @abstractmethod
    async def search(self, query: str, limit: int = 10, sort_by: str = "relevance") -> list[dict]:
        """搜索论文"""
        pass

    @abstractmethod
    async def get_paper(self, paper_id: str) -> Optional[dict]:
        """获取论文详情

        Args:
            paper_id: 论文 ID

        Returns:
            论文详情字典，未找到返回 None
        """
        pass

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
