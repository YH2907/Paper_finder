"""OpenAlex 爬虫实现

使用 OpenAlex API 获取学术论文。
OpenAlex 是一个开放的学术论文数据库，无需 API Key 即可使用。
文档: https://docs.openalex.org/
"""

import asyncio
from typing import Optional

from .base import BaseCrawler

# OpenAlex API 地址
OPENALEX_API_URL = "https://api.openalex.org/works"

# 用于标识邮件（遵循 OpenAlex 的礼貌使用政策）
MAILTO = "paper-finder-agent@example.com"


class OpenAlexCrawler(BaseCrawler):
    """OpenAlex 论文爬虫

    优点：
    - 免费，无需 API Key
    - 覆盖范围广（数百万篇论文）
    - 支持多种排序方式
    - 返回丰富元数据
    """

    def __init__(self, rate_limit: float = 1.0):
        """初始化 OpenAlex 爬虫

        Args:
            rate_limit: 请求间隔（秒）
        """
        super().__init__(rate_limit=rate_limit)

    async def search(self, query: str, limit: int = 10, sort_by: str = "relevance") -> list[dict]:
        """搜索 OpenAlex 论文

        Args:
            query: 搜索关键词
            limit: 返回结果数量
            sort_by: 排序方式 - "relevance"、"newest"、"cited_by_count"
        """
        limit = min(limit, 100)  # OpenAlex 最大 200，我们限制为 100

        # 排序映射
        sort_map = {
            "relevance": "relevance_score:desc",
            "newest": "publication_date:desc",
            "cited_by_count": "cited_by_count:desc",
            "submittedDate": "publication_date:desc",
            "oldest": "publication_date:asc",
        }
        sort = sort_map.get(sort_by, "relevance_score:desc")

        params = {
            "search": query,
            "per_page": limit,
            "page": 1,
            "sort": sort,
            "mailto": MAILTO,
        }

        try:
            response = await self.client.get(OPENALEX_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            works = data.get("results", [])
            return [self._normalize_paper(work) for work in works if work]

        except Exception as e:
            print(f"[OpenAlex] 搜索失败: {e}")
            return []

    async def get_paper(self, paper_id: str) -> Optional[dict]:
        """获取 OpenAlex 论文详情

        Args:
            paper_id: OpenAlex Work ID（如 W2741809807）
        Returns:
            论文详情字典，未找到返回 None
        """
        # 如果是 DOI 格式
        if paper_id.startswith("10.") or "/" in paper_id:
            url = f"https://api.openalex.org/works/doi:{paper_id}"
        else:
            # OpenAlex ID 格式
            url = f"https://api.openalex.org/works/{paper_id}"

        params = {"mailto": MAILTO}

        try:
            response = await self.client.get(url, params=params)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return self._normalize_paper(response.json())

        except Exception as e:
            print(f"[OpenAlex] 获取论文详情失败: {e}")
            return None

    def _normalize_paper(self, work: dict) -> dict:
        """将 OpenAlex 的数据格式转为标准格式

        Args:
            work: 原始论文数据
        Returns:
            标准化的论文字典
        """
        # 提取标题
        title = work.get("title", "") or work.get("display_name", "")

        # 提取作者
        authors = []
        authorships = work.get("authorships", [])
        for authorship in authorships:
            author = authorship.get("author", {})
            name = author.get("display_name", "") or author.get("name", "")
            if name:
                authors.append(name)

        # 提取 DOI
        doi = work.get("doi", "") or ""
        # OpenAlex 的 DOI 格式是 URL，需要转换
        if doi.startswith("https://doi.org/"):
            doi = doi[len("https://doi.org/"):]

        # 提取 PDF URL（优先使用 OA 链接）
        pdf_url = ""
        oa = work.get("open_access", {})
        if oa and oa.get("is_oa"):
            pdf_url = oa.get("oa_url", "") or ""
            # oa_url 可能是 None
            if not pdf_url:
                locations = work.get("locations", [])
                for loc in locations:
                    if loc and loc.get("pdf_url"):
                        pdf_url = loc["pdf_url"]
                        break

        # 提取 URL
        url = work.get("id", "") or ""
        # 优先使用期刊 URL
        locations = work.get("locations", [])
        for loc in locations:
            if loc and loc.get("source") and loc["source"].get("host_organization_name"):
                source_url = loc.get("source", {}).get("homepage_url", "")
                if source_url:
                    url = source_url
                    break

        # 提取年份和日期
        publication_date = work.get("publication_date", "")
        year = work.get("publication_year", 0)

        # 提取分类/领域
        categories = []
        concepts = work.get("concepts", [])
        for concept in concepts:
            name = concept.get("display_name", "")
            if name and len(categories) < 10:  # 最多 10 个分类
                categories.append(name)

        # 提取引用计数
        citation_count = work.get("cited_by_count", 0)

        # 提取开放获取信息
        is_open_access = oa.get("is_oa", False) if oa else False

        result = {
            "id": work.get("id", "").split("/")[-1],  # 提取 ID
            "source": "openalex",
            "title": title,
            "abstract": self._reconstruct_abstract(work.get("abstract_inverted_index", {})),
            "authors": authors,
            "url": url,
            "pdf_url": pdf_url,
            "doi": doi,
            "published": publication_date or (str(year) if year else ""),
            "year": year,
            "citation_count": citation_count,
            "categories": categories,
            "is_open_access": is_open_access,
            "publication_type": work.get("type", ""),
        }

        return result

    def _reconstruct_abstract(self, inverted_index: dict) -> str:
        """从 OpenAlex 的倒排索引中重建摘要

        OpenAlex 将摘要存储为倒排索引格式，需要重建为完整文本。

        Args:
            inverted_index: 倒排索引字典（可能为 None）
        Returns:
            重建的摘要文本
        """
        if not inverted_index or not isinstance(inverted_index, dict):
            return ""

        # 收集所有单词及其位置
        word_positions = []
        for word, positions in inverted_index.items():
            if positions is None:
                continue
            for pos in positions:
                word_positions.append((pos, word))

        # 按位置排序
        word_positions.sort(key=lambda x: x[0])

        # 重建文本
        return " ".join(word for _, word in word_positions)
