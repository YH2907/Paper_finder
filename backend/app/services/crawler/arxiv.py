"""arXiv 爬虫 - Supabase 兼容版

使用 arXiv API 搜索预印本论文。
文档: https://arxiv.org/help/api
"""

import xml.etree.ElementTree as ET
from typing import Optional

import httpx

# arXiv API 地址
ARXIV_API_URL = "https://export.arxiv.org/api/query"

# Atom XML namespace
ATOM_NS = "{http://www.w3.org/2005/Atom}"
OPENSEARCH_NS = "{http://a9.com/-/spec/opensearch/1.1/}"


class ArxivCrawler:
    """arXiv 论文爬虫"""

    def __init__(self, rate_limit: float = 1.0):
        self.rate_limit = rate_limit
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "PaperFinderAgent/1.0 (research)"},
        )

    async def search(self, query: str, limit: int = 10, sort_by: str = "relevance") -> list[dict]:
        """搜索 arXiv 论文"""
        # 正确构建 search_query
        # 输入可能是 "AGV OR deadlock OR scheduling"（已含 OR）
        # 需要识别已有的 OR 运算符，不要把它当关键词
        import re
        # 先按 " OR " 分割，得到纯关键词组
        or_groups = re.split(r'\bOR\b', query)
        search_parts = []
        for group in or_groups:
            group = group.strip()
            if not group:
                continue
            # 每个 group 内可能含空格（多词 AND）
            words = group.split()
            for word in words:
                if ":" in word:
                    search_parts.append(word)
                else:
                    search_parts.append(f"all:{word}")
        search_query = "+OR+".join(search_parts)

        # 排序映射
        sort_map = {
            "relevance": ("relevance", "descending"),
            "newest": ("lastUpdatedDate", "descending"),
            "submittedDate": ("submittedDate", "descending"),
            "oldest": ("submittedDate", "ascending"),
        }
        sort_by_val, sort_order = sort_map.get(sort_by, ("relevance", "descending"))

        # 手动拼接 URL 避免 httpx 参数编码问题
        url = f"{ARXIV_API_URL}?search_query={search_query}&start=0&max_results={limit}&sortBy={sort_by_val}&sortOrder={sort_order}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return self._parse_xml(response.text)
        except Exception as e:
            print(f"[arXiv] 搜索失败: {e}")
            # 回退：只用第一个关键词
            if len(search_parts) > 1:
                try:
                    fallback_url = f"{ARXIV_API_URL}?search_query={search_parts[0]}&start=0&max_results={limit}&sortBy={sort_by_val}&sortOrder={sort_order}"
                    response = await self.client.get(fallback_url)
                    response.raise_for_status()
                    return self._parse_xml(response.text)
                except Exception as e2:
                    print(f"[arXiv] 回退搜索也失败: {e2}")
            return []

    async def get_paper(self, paper_id: str) -> Optional[dict]:
        """获取论文详情"""
        # arXiv ID 格式：如 "2301.12345"
        url = f"{ARXIV_API_URL}?id_list={paper_id}&max_results=1"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            papers = self._parse_xml(response.text)
            return papers[0] if papers else None
        except Exception as e:
            print(f"[arXiv] 获取详情失败: {e}")
            return None

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()

    def _parse_xml(self, xml_text: str) -> list[dict]:
        """解析 arXiv API 返回的 Atom XML"""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        papers = []
        for entry in root.findall(f"{ATOM_NS}entry"):
            paper = self._parse_entry(entry)
            if paper:
                papers.append(paper)

        return papers

    def _parse_entry(self, entry) -> Optional[dict]:
        """解析单个 Atom entry"""
        # 标题
        title_el = entry.find(f"{ATOM_NS}title")
        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        if not title:
            return None

        # 摘要
        summary_el = entry.find(f"{ATOM_NS}summary")
        abstract = summary_el.text.strip() if summary_el is not None and summary_el.text else ""

        # 作者
        authors = []
        for author_el in entry.findall(f"{ATOM_NS}author"):
            name_el = author_el.find(f"{ATOM_NS}name")
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        # arXiv ID
        id_el = entry.find(f"{ATOM_NS}id")
        arxiv_url = id_el.text.strip() if id_el is not None and id_el.text else ""
        arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else ""

        # 链接
        pdf_url = ""
        abs_url = ""
        for link_el in entry.findall(f"{ATOM_NS}link"):
            if link_el.get("title") == "pdf":
                pdf_url = link_el.get("href", "")
            elif link_el.get("type") == "text/html":
                abs_url = link_el.get("href", "")

        # 发布时间
        published_el = entry.find(f"{ATOM_NS}published")
        updated_el = entry.find(f"{ATOM_NS}updated")
        published = ""
        if updated_el is not None and updated_el.text:
            published = updated_el.text[:10]
        elif published_el is not None and published_el.text:
            published = published_el.text[:10]

        # 分类
        categories = []
        for cat_el in entry.findall(f"{ATOM_NS}category"):
            term = cat_el.get("term", "")
            if term:
                categories.append(term)

        return {
            "id": arxiv_id,
            "source": "arxiv",
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "url": abs_url or arxiv_url,
            "pdf_url": pdf_url,
            "published": published,
            "categories": categories,
            "arxiv_id": arxiv_id,
            "doi": "",
        }
