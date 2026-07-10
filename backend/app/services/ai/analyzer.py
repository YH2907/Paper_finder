"""论文分析服务

封装 AI 路由器，提供高层论文分析功能。
"""

from typing import Optional

from .router import AIRouter


class PaperAnalyzer:
    """论文分析服务"""

    def __init__(self, ai_router: AIRouter):
        """初始化论文分析服务

        Args:
            ai_router: AI 路由器实例
        """
        self.ai_router = ai_router

    async def analyze(self, title: str, abstract: str) -> dict:
        """分析论文，生成摘要和问题分析

        Args:
            title: 论文标题
            abstract: 论文摘要

        Returns:
            分析结果字典，包含:
            - summary: 核心内容摘要
            - problems: 解决的问题列表
            - keywords: 关键词列表
            - methodology: 方法论描述
            - significance: 意义和贡献
        """
        if not abstract or not abstract.strip():
            return {
                "summary": "无摘要信息",
                "problems": [],
                "keywords": [],
                "methodology": "",
                "significance": "",
            }

        result = await self.ai_router.analyze_paper(title, abstract)

        # 确保返回结构完整
        return {
            "summary": result.get("summary", ""),
            "problems": result.get("problems", []),
            "keywords": result.get("keywords", []),
            "methodology": result.get("methodology", ""),
            "significance": result.get("significance", ""),
        }

    async def generate_summary(self, title: str, abstract: str) -> str:
        """生成论文摘要

        Args:
            title: 论文标题
            abstract: 论文摘要

        Returns:
            中文摘要文本
        """
        result = await self.analyze(title, abstract)
        return result.get("summary", "")

    async def find_problems(self, title: str, abstract: str) -> list[str]:
        """分析论文试图解决的问题

        Args:
            title: 论文标题
            abstract: 论文摘要

        Returns:
            问题列表
        """
        result = await self.analyze(title, abstract)
        return result.get("problems", [])

    async def batch_analyze(self, papers: list[dict]) -> list[dict]:
        """批量分析论文

        Args:
            papers: 论文列表，每个元素需包含 title 和 abstract 字段

        Returns:
            带有 analysis 字段的论文列表
        """
        analyzed = []
        for paper in papers:
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")

            try:
                analysis = await self.analyze(title, abstract)
                paper["analysis"] = analysis
            except Exception as e:
                print(f"[Analyzer] 分析论文失败: {title[:50]}... - {e}")
                paper["analysis"] = {
                    "summary": "",
                    "problems": [],
                    "keywords": [],
                    "methodology": "",
                    "significance": "",
                }

            analyzed.append(paper)

        return analyzed
