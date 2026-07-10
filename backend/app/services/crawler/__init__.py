# 爬虫服务模块
# 数据源：arXiv、Semantic Scholar、IEEE Xplore、OpenAlex

from .arxiv import ArxivCrawler
from .base import BaseCrawler
from .engine import CrawlerEngine
from .ieee import IEEECrawler
from .openalex import OpenAlexCrawler
from .semantic_scholar import SemanticScholarCrawler

__all__ = [
    "BaseCrawler",
    "ArxivCrawler",
    "SemanticScholarCrawler",
    "IEEECrawler",
    "OpenAlexCrawler",
    "CrawlerEngine",
]
