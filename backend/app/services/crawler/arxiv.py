"""arXiv 爬虫实现"""

import asyncio
import re
import xml.etree.ElementTree as ET
from typing import Optional
from .base import BaseCrawler

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivCrawler(BaseCrawler):
    """arXiv 论文爬虫"""

    def __init__(self, rate_limit: float = 3.0):
        super().__init__(rate_limit=rate_limit)

    async def search(self, query: str, limit: int = 10, sort_by: str = "relevance") -> list[dict]:
        """搜索 arXiv 论文

        Args:
            query: 搜索关键词
            limit: 返回结果数量
            sort_by: 排序方式 - "relevance" (相关性) 或 "submittedDate" (最新)
        """
        limit = min(limit, 100)
        # 清理查询：去除无效字符，处理 OR 语法
        query = query.replace("，", " ").replace(",", " ").strip()
        # 处理 "keyword1 OR keyword2 OR keyword3" 格式
        parts = [p.strip() for p in query.split(" OR ") if p.strip()]
        if len(parts) > 1:
            # 多个关键词用 OR 连接，每个词加 all: 前缀
            search_query = " OR ".join(f"all:{p}" for p in parts)
        else:
            search_query = f"all:{query}"

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": limit,
            "sortBy": sort_by,
            "sortOrder": "descending",
        }

        try:
            response = await self.client.get(ARXIV_API_URL, params=params)
            response.raise_for_status()
            return self._parse_response(response.text)
        except Exception as e:
            print(f"[arXiv] 搜索失败: {e}")
            return []

    async def get_paper(self, paper_id: str) -> Optional[dict]:
        params = {"id_list": paper_id, "max_results": 1}
        try:
            response = await self.client.get(ARXIV_API_URL, params=params)
            response.raise_for_status()
            papers = self._parse_response(response.text)
            return papers[0] if papers else None
        except Exception as e:
            print(f"[arXiv] 获取论文详情失败: {e}")
            return None

    def _parse_response(self, xml_text: str) -> list[dict]:
        papers = []
        try:
            root = ET.fromstring(xml_text)
            for entry in root.findall("atom:entry", ARXIV_NS):
                paper = self._parse_entry(entry)
                if paper:
                    papers.append(paper)
        except ET.ParseError as e:
            print(f"[arXiv] XML 解析错误: {e}")
        return papers

    def _parse_entry(self, entry) -> Optional[dict]:
        try:
            title = entry.find("atom:title", ARXIV_NS)
            title_text = title.text.strip().replace("\n", " ") if title is not None else ""
            title_text = re.sub(r"\s+", " ", title_text)

            summary = entry.find("atom:summary", ARXIV_NS)
            summary_text = summary.text.strip().replace("\n", " ") if summary is not None else ""
            summary_text = re.sub(r"\s+", " ", summary_text)

            authors = []
            for author in entry.findall("atom:author", ARXIV_NS):
                name = author.find("atom:name", ARXIV_NS)
                if name is not None:
                    authors.append(name.text.strip())

            pdf_url = ""
            abs_url = ""
            for link in entry.findall("atom:link", ARXIV_NS):
                if link.get("title") == "pdf" or "pdf" in link.get("type", ""):
                    pdf_url = link.get("href", "")
                elif link.get("rel") == "alternate":
                    abs_url = link.get("href", "")

            id_elem = entry.find("atom:id", ARXIV_NS)
            arxiv_id = ""
            if id_elem is not None:
                id_text = id_elem.text.strip()
                arxiv_id = id_text.split("/abs/")[-1] if "/abs/" in id_text else id_text

            published = entry.find("atom:published", ARXIV_NS)
            pub_date = published.text.strip() if published is not None else ""

            categories = [cat.get("term", "") for cat in entry.findall("atom:category", ARXIV_NS) if cat.get("term")]

            doi_elem = entry.find("arxiv:doi", ARXIV_NS)
            doi = doi_elem.text.strip() if doi_elem is not None else ""

            return {
                "id": arxiv_id, "source": "arxiv", "title": title_text,
                "abstract": summary_text, "authors": authors,
                "url": abs_url, "pdf_url": pdf_url,
                "published": pub_date, "categories": categories, "doi": doi,
            }
        except Exception as e:
            print(f"[arXiv] 解析条目失败: {e}")
            return None
