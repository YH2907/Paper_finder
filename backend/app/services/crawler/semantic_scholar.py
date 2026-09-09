"""Semantic Scholar 爬虫实现

使用 Semantic Scholar API 搜索学术论文
文档: https://api.semanticscholar.org/
"""

import asyncio
from typing import Optional

from .base import BaseCrawler

# Semantic Scholar API 地址
S2_API_BASE = "https://api.semanticscholar.org/graph/v1"

# 请求字段（搜索结果）
SEARCH_FIELDS = "paperId,title,abstract,authors,url,year,citationCount,openAccessPdf,externalIds"

# 请求字段（论文详情）
DETAIL_FIELDS = "paperId,title,abstract,authors,url,year,citationCount,referenceCount,openAccessPdf,externalIds,tldr,fieldsOfStudy,venue,publicationDate"


class SemanticScholarCrawler(BaseCrawler):
    """Semantic Scholar 论文爬虫"""

    def __init__(self, rate_limit: float = 1.0, api_key: str = None):
        """初始化 Semantic Scholar 爬虫

        Args:
            rate_limit: 请求间隔（秒）
            api_key: API 密钥（可选，有密钥时速率限制更宽松）
        """
        super().__init__(rate_limit=rate_limit)
        self.api_key = api_key
        if api_key:
            self.client.headers["x-api-key"] = api_key

    async def search(self, query: str, limit: int = 10, sort_by: str = "relevance") -> list[dict]:
        """搜索 Semantic Scholar 论文"""
        limit = min(limit, 100)
        url = f"{S2_API_BASE}/paper/search"

        params = {
            "query": query,
            "limit": limit,
            "fields": SEARCH_FIELDS,
        }

        try:
            response = await self.client.get(url, params=params)
            if response.status_code == 429:
                # 限流，等待后重试一次
                import asyncio
                await asyncio.sleep(2)
                response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            papers = data.get("data", [])
            return [self._normalize_paper(p) for p in papers if p]
        except Exception as e:
            print(f"[SemanticScholar] 搜索失败: {e}")
            return []

    async def get_paper(self, paper_id: str) -> Optional[dict]:
        """获取 Semantic Scholar 论文详情

        Args:
            paper_id: 论文 ID（S2 paperId 或外部 ID，如 DOI）

        Returns:
            论文详情字典，未找到返回 None
        """
        # 支持多种 ID 格式
        if paper_id.startswith("10.") or "/" in paper_id:
            # DOI 格式
            url = f"{S2_API_BASE}/paper/DOI:{paper_id}"
        elif paper_id.startswith("ARXIV:"):
            url = f"{S2_API_BASE}/paper/{paper_id}"
        else:
            url = f"{S2_API_BASE}/paper/{paper_id}"

        params = {"fields": DETAIL_FIELDS}

        try:
            response = await self.client.get(url, params=params)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return self._normalize_paper(response.json(), detail=True)
        except Exception as e:
            print(f"[SemanticScholar] 获取论文详情失败: {e}")
            return None

    def _normalize_paper(self, paper: dict, detail: bool = False) -> dict:
        """将 Semantic Scholar 的数据格式转为标准格式

        Args:
            paper: 原始论文字典
            detail: 是否为详情数据

        Returns:
            标准化的论文字典
        """
        # 提取作者
        authors = []
        for author in paper.get("authors", []):
            name = author.get("name", "")
            if name:
                authors.append(name)

        # 提取 PDF 链接
        pdf_url = ""
        oa_pdf = paper.get("openAccessPdf")
        if oa_pdf and isinstance(oa_pdf, dict):
            pdf_url = oa_pdf.get("url", "")

        # 提取外部 ID
        external_ids = paper.get("externalIds", {}) or {}
        doi = external_ids.get("DOI", "")
        arxiv_id = external_ids.get("ArXiv", "")

        # 构建标准结果
        result = {
            "id": paper.get("paperId", ""),
            "source": "semantic_scholar",
            "title": paper.get("title", ""),
            "abstract": paper.get("abstract", "") or "",
            "authors": authors,
            "url": paper.get("url", ""),
            "pdf_url": pdf_url,
            "year": paper.get("year"),
            "citation_count": paper.get("citationCount", 0),
            "doi": doi,
            "arxiv_id": arxiv_id,
            "categories": paper.get("fieldsOfStudy", []) or [],
        }

        # 详情模式下添加额外字段
        if detail:
            result["reference_count"] = paper.get("referenceCount", 0)
            result["venue"] = paper.get("venue", "")
            result["publication_date"] = paper.get("publicationDate", "")

            # TLDR 摘要
            tldr = paper.get("tldr")
            if tldr and isinstance(tldr, dict):
                result["tldr"] = tldr.get("text", "")
            else:
                result["tldr"] = ""

        return result
