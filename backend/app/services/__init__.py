"""服务层模块

提供论文爬虫、AI 分析和通知分发功能。
"""

from .ai.analyzer import PaperAnalyzer
from .ai.chat import ChatService
from .ai.router import AIRouter
from .crawler.engine import CrawlerEngine
from .notification.dispatcher import NotificationDispatcher
from .paper_service import PaperService

__all__ = [
    "CrawlerEngine",
    "AIRouter",
    "PaperAnalyzer",
    "PaperService",
    "ChatService",
    "NotificationDispatcher",
]
