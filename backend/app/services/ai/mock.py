"""Mock AI 服务

在没有配置真实 AI API Key 时使用，返回模拟的 AI 回复用于开发和测试。
"""
import asyncio
import json
import random
import time
from typing import AsyncGenerator

from .base import BaseAIService


class MockAIService(BaseAIService):
    """Mock AI 服务：返回预设的模拟回复"""

    def __init__(self):
        self.call_count = 0

    async def chat(self, messages: list[dict], model: str = None) -> str:
        """模拟对话回复

        Args:
            messages: 消息列表
            model: 模型名称（忽略）

        Returns:
            模拟的 AI 回复文本
        """
        self.call_count += 1

        # 获取用户最后一条消息
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        # 根据用户消息生成模拟回复
        reply = self._generate_reply(user_message)
        return reply

    async def chat_stream(
        self, messages: list[dict], model: str = None
    ) -> AsyncGenerator[str, None]:
        """模拟流式对话 — 逐字返回回复

        Args:
            messages: 消息列表
            model: 模型名称（忽略）

        Yields:
            逐个字符的文本片段
        """
        self.call_count += 1

        # 获取用户最后一条消息
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        # 生成模拟回复
        reply = self._generate_reply(user_message)

        # 模拟逐字流式输出
        for char in reply:
            yield char
            # 模拟网络延迟，让前端可以展示流式效果
            await asyncio.sleep(0.02)

    async def analyze_paper(self, title: str, abstract: str) -> dict:
        """模拟论文分析

        Args:
            title: 论文标题
            abstract: 论文摘要

        Returns:
            模拟的分析结果字典
        """
        self.call_count += 1
        # 从标题和摘要中提取关键词（简单的模拟）
        keywords = self._extract_mock_keywords(title, abstract)

        return {
            "summary": f"[Mock 模式] 本文《{title}》主要研究了相关领域的核心问题，"
                       f"提出了一种新的方法来解决现有挑战。研究结果表明该方法具有良好的效果。",
            "problems": [
                f"[Mock] 现有方法在处理{keywords[0] if keywords else '该问题'}时存在局限性",
                f"[Mock] 缺乏对{keywords[1] if len(keywords) > 1 else '相关场景'}的有效解决方案",
            ],
            "keywords": keywords[:5],
            "methodology": f"[Mock] 采用了基于{keywords[0] if keywords else '深度学习'}的方法论",
            "significance": f"[Mock] 本研究对{keywords[0] if keywords else '该领域'}的发展具有重要推动意义",
        }

    def _generate_reply(self, user_message: str) -> str:
        """根据用户消息生成模拟回复

        Args:
            user_message: 用户消息

        Returns:
            模拟回复
        """
        # 常见问题的模拟回复模板
        replies = [
            f"您好！感谢您的提问。关于「{user_message[:30]}」这个问题，"
            f"这是一个很好的研究方向。在学术领域中，这类问题通常涉及到多个方面的考量。\n\n"
            f"（此回复由 Mock AI 服务生成，配置真实 AI API Key 后可获得更准确的回答）",
            f"这是一个有趣的问题。根据我的理解，您想了解关于「{user_message[:20]}」的内容。\n\n"
            f"建议您可以从以下几个角度来思考：\n"
            f"1. 相关领域的经典文献\n"
            f"2. 最新的研究进展\n"
            f"3. 实际应用场景\n\n"
            f"（此回复由 Mock AI 服务生成，配置真实 AI API Key 后可获得更准确的回答）",
            f"感谢您的消息！关于「{user_message[:25]}」，"
            f"我建议您可以查阅相关领域的最新论文来获取更详细的信息。\n\n"
            f"如果您需要帮助搜索论文或分析论文内容，请随时告诉我。\n\n"
            f"（此回复由 Mock AI 服务生成，配置真实 AI API Key 后可获得更准确的回答）",
        ]

        return random.choice(replies)

    def _extract_mock_keywords(self, title: str, abstract: str) -> list[str]:
        """从标题和摘要中提取模拟关键词

        Args:
            title: 论文标题
            abstract: 论文摘要

        Returns:
            关键词列表
        """
        # 简单的关键词提取：按空格分割标题，取较长的词
        words = title.split()
        keywords = [w for w in words if len(w) > 3 and w.isalpha()]

        # 如果关键词不够，添加一些通用的
        default_keywords = ["机器学习", "深度学习", "自然语言处理", "计算机视觉", "人工智能"]
        while len(keywords) < 3:
            kw = default_keywords[len(keywords) % len(default_keywords)]
            if kw not in keywords:
                keywords.append(kw)

        return keywords[:5]

    async def close(self):
        """关闭服务（Mock 服务无需操作）"""
        pass
