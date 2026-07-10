"""AI 服务基类"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseAIService(ABC):
    """AI 服务基类"""

    @abstractmethod
    async def chat(self, messages: list[dict], model: str = None) -> str:
        """对话接口

        Args:
            messages: 消息列表，每条消息包含 role 和 content
            model: 模型名称，为 None 时使用默认模型

        Returns:
            AI 回复文本
        """
        pass

    async def chat_stream(
        self, messages: list[dict], model: str = None
    ) -> AsyncGenerator[str, None]:
        """流式对话接口（默认实现：回退到非流式）

        Args:
            messages: 消息列表，每条消息包含 role 和 content
            model: 模型名称，为 None 时使用默认模型

        Yields:
            AI 回复的逐块文本片段
        """
        result = await self.chat(messages, model)
        # 默认实现：将完整回复一次性 yield，兼容不支持流式的 AI 服务
        yield result

    @abstractmethod
    async def analyze_paper(self, title: str, abstract: str) -> dict:
        """分析论文

        Args:
            title: 论文标题
            abstract: 论文摘要

        Returns:
            分析结果字典，包含 summary, problems, keywords 等字段
        """
        pass
