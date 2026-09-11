"""爬虫引擎

并发调用多个爬虫源，合并结果并去重。
支持的数据源：arXiv、Semantic Scholar、IEEE Xplore、OpenAlex、Crossref。
"""

import asyncio
from typing import Optional

from .arxiv import ArxivCrawler
from .base import BaseCrawler
from .crossref import CrossrefCrawler
from .ieee import IEEECrawler
from .openalex import OpenAlexCrawler
from .semantic_scholar import SemanticScholarCrawler


class CrawlerEngine:
    """爬虫引擎：统一调度多个数据源

    支持的数据源：
    - arXiv: 预印本服务器
    - Semantic Scholar: 学术搜索引擎
    - IEEE Xplore: 电子工程与计算机科学文献库
    - OpenAlex: 开放的学术论文数据库
    - Crossref: DOI 注册机构，1.5 亿+ 期刊文献
    """

    def __init__(self, ieee_api_key: str = None):
        """初始化爬虫引擎，注册所有可用爬虫

        Args:
            ieee_api_key: IEEE Xplore API Key（可选）
        """
        self.crawlers: list[BaseCrawler] = [
            ArxivCrawler(),
            SemanticScholarCrawler(),
            IEEECrawler(api_key=ieee_api_key),
            OpenAlexCrawler(),
            CrossrefCrawler(),
        ]

        # 构建数据源名称映射
        self._name_map = {
            "arxiv": self.crawlers[0],
            "semantic_scholar": self.crawlers[1],
            "ieee": self.crawlers[2],
            "openalex": self.crawlers[3],
            "crossref": self.crawlers[4],
        }

    async def search(self, query: str, limit: int = 10, sources: list[str] = None, sort_by: str = "relevance") -> list[dict]:
        """并发搜索多个数据源，合并去重结果

        Args:
            query: 搜索关键词
            limit: 每个数据源返回的结果数量
            sources: 指定的数据源列表（None 表示全部）
            sort_by: 排序方式
        Returns:
            去重后的论文列表
        """
        crawlers = self._filter_crawlers(sources)
        tasks = [crawler.search(query, limit, sort_by=sort_by) for crawler in crawlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_papers = []
        for result in results:
            if isinstance(result, list):
                all_papers.extend(result)
            elif isinstance(result, Exception):
                print(f"[Engine] 爬虫执行异常: {result}")

        # 去重并排序
        unique_papers = self._deduplicate(all_papers)
        return self._sort_papers(unique_papers, sort_by)

    async def search_multi_query(self, queries: list[str], limit_per_query: int = 10, sources: list[str] = None, sort_by: str = "relevance") -> list[dict]:
        """使用多个查询并发搜索

        Args:
            queries: 查询列表
            limit_per_query: 每个查询返回的结果数量
            sources: 指定的数据源列表
            sort_by: 排序方式
        Returns:
            去重后的论文列表
        """
        if not queries:
            return []

        crawlers = self._filter_crawlers(sources)
        tasks = []

        # 为每个爬虫分配所有查询
        for crawler in crawlers:
            for query in queries:
                tasks.append(crawler.search(query, limit_per_query, sort_by=sort_by))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_papers = []
        for result in results:
            if isinstance(result, list):
                all_papers.extend(result)
            elif isinstance(result, Exception):
                print(f"[Engine] 多查询搜索异常: {result}")

        # 去重并排序
        unique_papers = self._deduplicate(all_papers)
        return self._sort_papers(unique_papers, sort_by)

    async def get_paper(self, paper_id: str, source: str) -> Optional[dict]:
        """从指定数据源获取论文详情

        Args:
            paper_id: 论文 ID
            source: 数据源名称
        Returns:
            论文详情字典，未找到返回 None
        """
        crawler = self._get_crawler(source)
        if not crawler:
            print(f"[Engine] 未找到数据源: {source}")
            return None

        return await crawler.get_paper(paper_id)

    async def close(self):
        """关闭所有爬虫的 HTTP 客户端"""
        tasks = [crawler.close() for crawler in self.crawlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    def get_available_sources(self) -> list[str]:
        """获取所有可用的数据源名称

        Returns:
            数据源名称列表
        """
        return list(self._name_map.keys())

    def _filter_crawlers(self, sources: list[str] = None) -> list[BaseCrawler]:
        """根据数据源名称过滤爬虫

        Args:
            sources: 数据源名称列表
        Returns:
            过滤后的爬虫列表
        """
        if not sources:
            return self.crawlers

        filtered = []
        for name in sources:
            crawler = self._name_map.get(name)
            if crawler:
                filtered.append(crawler)

        return filtered if filtered else self.crawlers

    def _get_crawler(self, source: str) -> Optional[BaseCrawler]:
        """根据名称获取爬虫实例

        Args:
            source: 数据源名称
        Returns:
            爬虫实例，未找到返回 None
        """
        return self._name_map.get(source)

    def _deduplicate(self, papers: list[dict]) -> list[dict]:
        """对论文列表去重

        优先使用 DOI 去重，其次使用标题相似度去重。

        Args:
            papers: 论文列表
        Returns:
            去重后的论文列表
        """
        seen_dois = set()
        seen_titles = set()
        unique_papers = []

        for paper in papers:
            doi = paper.get("doi", "")
            title = paper.get("title", "").lower().strip()

            # 通过 DOI 去重
            if doi and doi in seen_dois:
                continue

            # 通过标题去重（允许一些差异）
            if title and title in seen_titles:
                continue

            # 记录已见标识
            if doi:
                seen_dois.add(doi)
            if title:
                seen_titles.add(title)

            unique_papers.append(paper)

        return unique_papers

    def _sort_papers(self, papers: list[dict], sort_by: str = "relevance") -> list[dict]:
        """对论文列表排序

        Args:
            papers: 论文列表
            sort_by: 排序方式
        Returns:
            排序后的论文列表
        """
        if sort_by == "newest" or sort_by == "submittedDate":
            # 按发布时间降序
            return sorted(
                papers,
                key=lambda p: p.get("published", "") or "0000",
                reverse=True,
            )
        elif sort_by == "cited_by_count":
            # 按引用量降序
            return sorted(
                papers,
                key=lambda p: p.get("citation_count", 0),
                reverse=True,
            )
        else:
            # 默认按相关性（保持原始顺序）
            return papers
