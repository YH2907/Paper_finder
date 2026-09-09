"""IEEE Xplore 爬虫实现

使用 IEEE Xplore 搜索 API 获取论文。
IEEE Xplore 提供免费的 REST API（https://developer.ieee.org/），
但需要注册获取 API Key。如果没有 API Key，则使用网页搜索接口。
"""

import asyncio
import os
from typing import Optional

from .base import BaseCrawler

# IEEE Xplore API 地址
IEEE_API_URL = "https://ieeexploreapi.ieee.org/api/v1/search/articles"

# 论文详情 API
IEEE_DETAIL_URL = "https://ieeexploreapi.ieee.org/api/v1/search/articles"


class IEEECrawler(BaseCrawler):
    """IEEE Xplore 论文爬虫

    支持两种模式：
    1. 有 API Key：使用官方 API（更稳定、更快）
    2. 无 API Key：使用网页搜索接口（可能不稳定）
    """

    def __init__(self, rate_limit: float = 2.0, api_key: str = None):
        """初始化 IEEE 爬虫

        Args:
            rate_limit: 请求间隔（秒）
            api_key: API 密钥（可选）
        """
        super().__init__(rate_limit=rate_limit)
        self.api_key = api_key or os.getenv("IEEE_API_KEY", "")

    async def search(self, query: str, limit: int = 10, sort_by: str = "relevance") -> list[dict]:
        """搜索 IEEE Xplore 论文

        Args:
            query: 搜索关键词
            limit: 返回结果数量
            sort_by: 排序方式 - "relevance" 或 "newest"
        """
        limit = min(limit, 50)  # IEEE API 限制

        if self.api_key:
            return await self._search_with_api(query, limit, sort_by)
        else:
            return await self._search_without_api(query, limit, sort_by)

    async def _search_with_api(self, query: str, limit: int, sort_by: str) -> list[dict]:
        """使用 IEEE 官方 API 搜索"""
        # 排序映射
        sort_map = {
            "relevance": "relevance",
            "newest": "newest",
            "oldest": "oldest",
            "submittedDate": "newest",
        }
        sort_field = sort_map.get(sort_by, "relevance")

        params = {
            "apikey": self.api_key,
            "querytext": query,
            "max_records": limit,
            "start_record": 1,
            "sortfield": sort_field,
            "sortorder": "desc",
        }

        try:
            response = await self.client.get(IEEE_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            articles = data.get("articles", [])
            return [self._normalize_paper(article) for article in articles if article]

        except Exception as e:
            print(f"[IEEE] API 搜索失败: {e}")
            # 回退到无 API 模式
            return await self._search_without_api(query, limit, sort_by)

    async def _search_without_api(self, query: str, limit: int, sort_by: str) -> list[dict]:
        """无 API Key 时使用网页搜索接口

        IEEE Xplore 提供了一个用于学术搜索的接口
        """
        try:
            # 使用 IEEE Xplore 的公开搜索接口
            search_url = "https://ieeexplore.ieee.org/rest/search"
            headers = {
                "Content-Type": "application/json",
                "Referer": "https://ieeexplore.ieee.org/search/searchresult.jsp",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }

            # 构建搜索请求
            sort_map = {
                "relevance": "Best Match",
                "newest": "Newest First",
                "oldest": "Oldest First",
                "submittedDate": "Newest First",
            }
            sort_text = sort_map.get(sort_by, "Best Match")

            payload = {
                "queryText": query,
                "highlight": True,
                "returnFacets": ["ALL"],
                "returnType": "SEARCH",
                "pageNumber": 1,
                "rowsPerPage": limit,
                "sortField": sort_text,
            }

            response = await self.client.post(search_url, json=payload, headers=headers)

            if response.status_code != 200:
                print(f"[IEEE] 网页搜索返回状态码 {response.status_code}")
                return []

            data = response.json()
            articles = data.get("records", [])
            return [self._normalize_paper(record) for record in articles if record]

        except Exception as e:
            print(f"[IEEE] 网页搜索失败: {e}")
            return []

    async def get_paper(self, paper_id: str) -> Optional[dict]:
        """获取 IEEE 论文详情

        Args:
            paper_id: IEEE 文章编号（如 12345678）
        Returns:
            论文详情字典，未找到返回 None
        """
        if not self.api_key:
            print("[IEEE] 获取论文详情需要 API Key")
            return None

        params = {
            "apikey": self.api_key,
            "article_number": paper_id,
        }

        try:
            response = await self.client.get(IEEE_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            articles = data.get("articles", [])
            if articles:
                return self._normalize_paper(articles[0])
            return None

        except Exception as e:
            print(f"[IEEE] 获取论文详情失败: {e}")
            return None

    def _normalize_paper(self, article: dict) -> dict:
        """将 IEEE API 返回的数据转为标准格式

        Args:
            article: 原始论文数据
        Returns:
            标准化的论文字典
        """
        # 提取作者
        authors = []
        for author in article.get("authors", []):
            if isinstance(author, dict):
                name = author.get("preferredName", "") or author.get("name", "")
            elif isinstance(author, str):
                name = author
            else:
                name = ""
            if name:
                authors.append(name)

        # 提取 DOI
        doi = article.get("doi", "")
        if not doi:
            doi = article.get("articleDOI", "")

        # 提取文章编号
        article_number = article.get("articleNumber", "") or article.get("article_number", "")

        # 构建 URL
        url = article.get("html_url", "") or article.get("url", "")
        if not url and article_number:
            url = f"https://ieeexplore.ieee.org/document/{article_number}"

        # 提取 PDF URL
        pdf_url = article.get("pdf_url", "") or ""
        if not pdf_url and article.get("pdfLink"):
            pdf_url = article["pdfLink"]

        # 提取年份
        year = article.get("publication_year", 0) or article.get("year", 0)

        # 构建标准结果
        result = {
            "id": str(article_number or article.get("articleNumber", "")),
            "source": "ieee",
            "title": article.get("title", ""),
            "abstract": article.get("abstract", "") or "",
            "authors": authors,
            "url": url,
            "pdf_url": pdf_url,
            "doi": doi,
            "published": str(year) if year else "",
            "categories": article.get("publication_title", []),
            "volume": article.get("volume", ""),
            "issue": article.get("issue", ""),
            "page_start": article.get("startPage", ""),
            "page_end": article.get("endPage", ""),
            "publisher": article.get("publisher", "IEEE"),
        }

        return result
