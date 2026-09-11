"""Crossref 爬虫实现

使用 Crossref REST API 获取学术论文元数据。
Crossref 是 DOI 注册机构，覆盖 1.5 亿+ 学术文献，无需 API Key。
文档: https://api.crossref.org/
"""

from typing import Optional

from .base import BaseCrawler

# Crossref API 地址
CROSSREF_API_URL = "https://api.crossref.org/works"

# 礼貌池（Polite Pool）：提供 mailto 可获得更稳定的速率
MAILTO = "paper-finder-agent@example.com"


class CrossrefCrawler(BaseCrawler):
    """Crossref 论文爬虫

    优点：
    - 免费，无需 API Key
    - 覆盖 1.5 亿+ 文献（期刊论文为主，与 arXiv 预印本互补）
    - 必带 DOI，去重可靠
    - 支持按相关性/时间排序
    """

    def __init__(self, rate_limit: float = 1.0):
        super().__init__(rate_limit=rate_limit)
        self.client.headers["User-Agent"] = f"PaperFinderAgent/1.0 (mailto:{MAILTO})"

    async def search(self, query: str, limit: int = 10, sort_by: str = "relevance") -> list[dict]:
        """搜索 Crossref 论文

        Args:
            query: 搜索关键词
            limit: 返回结果数量（Crossref 最大 1000，这里限制 100）
            sort_by: 排序方式 - "relevance"、"newest"、"cited_by_count"
        """
        limit = min(limit, 100)

        params = {
            "query": query,
            "rows": limit,
            "mailto": MAILTO,
            "select": "DOI,title,author,abstract,URL,container-title,published,is-referenced-by-count,type",
        }

        # 排序映射
        sort_map = {
            "newest": ("published", "desc"),
            "submittedDate": ("published", "desc"),
            "cited_by_count": ("is-referenced-by-count", "desc"),
            "oldest": ("published", "asc"),
        }
        if sort_by in sort_map:
            params["sort"] = sort_map[sort_by][0]
            params["order"] = sort_map[sort_by][1]
        # relevance 为 Crossref 默认排序，不传 sort

        try:
            response = await self.client.get(CROSSREF_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            items = data.get("message", {}).get("items", [])
            return [self._normalize_paper(item) for item in items if item]
        except Exception as e:
            print(f"[Crossref] 搜索失败: {e}")
            return []

    async def get_paper(self, paper_id: str) -> Optional[dict]:
        """获取 Crossref 论文详情

        Args:
            paper_id: DOI
        Returns:
            论文详情字典，未找到返回 None
        """
        if not paper_id:
            return None

        url = f"{CROSSREF_API_URL}/{paper_id}"
        try:
            response = await self.client.get(url, params={"mailto": MAILTO})
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return self._normalize_paper(response.json().get("message", {}))
        except Exception as e:
            print(f"[Crossref] 获取论文详情失败: {e}")
            return None

    def _normalize_paper(self, item: dict) -> dict:
        """将 Crossref 数据格式转为标准格式"""
        # 标题（Crossref 返回数组）
        titles = item.get("title") or []
        title = titles[0] if titles else ""

        # 作者
        authors = []
        for author in item.get("author") or []:
            name_parts = []
            if author.get("given"):
                name_parts.append(author["given"])
            if author.get("family"):
                name_parts.append(author["family"])
            if name_parts:
                authors.append(" ".join(name_parts))
            elif author.get("name"):
                authors.append(author["name"])

        # DOI
        doi = (item.get("DOI") or "").strip()

        # URL：优先 DOI 链接
        url = item.get("URL") or (f"https://doi.org/{doi}" if doi else "")

        # 摘要：Crossref 部分文献带 JATS XML 格式摘要，剥离标签
        abstract = self._clean_abstract(item.get("abstract") or "")

        # 发表日期
        published = ""
        pub = item.get("published") or {}
        date_parts = pub.get("date-parts") or [[]]
        if date_parts and date_parts[0]:
            parts = [str(p).zfill(2) for p in date_parts[0]]
            published = "-".join(parts)

        # 期刊/容器名
        container = item.get("container-title") or []
        journal = container[0] if container else ""

        # 引用数
        citation_count = item.get("is-referenced-by-count", 0)

        return {
            "id": doi or url,
            "source": "crossref",
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "url": url,
            "pdf_url": "",
            "doi": doi,
            "published": published,
            "journal": journal,
            "citation_count": citation_count,
            "categories": [],
            "publication_type": item.get("type", ""),
        }

    @staticmethod
    def _clean_abstract(abstract: str) -> str:
        """剥离 Crossref 摘要中的 JATS XML 标签"""
        if not abstract:
            return ""
        import re
        # 去掉所有 XML 标签
        text = re.sub(r"<[^>]+>", " ", abstract)
        # 压缩空白
        text = re.sub(r"\s+", " ", text).strip()
        return text
