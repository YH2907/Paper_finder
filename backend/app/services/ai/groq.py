"""Groq AI 服务实现

使用 Groq API 进行 LLM 对话
文档: https://console.groq.com/docs/api-reference
"""
import asyncio
import json
from typing import AsyncGenerator, Optional

import httpx
from .base import BaseAIService

# Groq API 地址
GROQ_API_URL = "https://api.groq.com/openai/v1"

# 默认模型（使用当前可用的模型）
DEFAULT_MODEL = "groq/compound"

# 论文分析提示词
PAPER_ANALYSIS_PROMPT = """你是一个学术论文分析助手。请分析以下论文，返回 JSON 格式的结果。

论文标题：{title}
论文摘要：{abstract}

请返回以下 JSON 格式的结果（不要包含其他文字）：
{{
    "summary": "用中文简洁总结论文的核心内容（100字以内）",
    "problems": ["论文试图解决的具体问题1", "论文试图解决的具体问题2"],
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "methodology": "论文使用的主要方法（50字以内）",
    "significance": "论文的意义和贡献（100字以内）"
}}"""


class GroqService(BaseAIService):
    """Groq AI 服务"""

    def __init__(self, api_key: str, model: str = None):
        """初始化 Groq 服务

        Args:
            api_key: Groq API 密钥
            model: 模型名称，默认为 llama3-70b-8192
        """
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def chat(self, messages: list[dict], model: str = None) -> str:
        """与 Groq LLM 对话

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            model: 模型名称，为 None 时使用默认模型

        Returns:
            AI 回复文本
        """
        url = f"{GROQ_API_URL}/chat/completions"
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as e:
            print(f"[Groq] API 错误: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            print(f"[Groq] 请求失败: {e}")
            raise

    async def chat_stream(
        self, messages: list[dict], model: str = None
    ) -> AsyncGenerator[str, None]:
        """流式对话 — 逐 token 返回 AI 回复

        使用 Groq 的 SSE streaming 接口，兼容 OpenAI 格式。

        Args:
            messages: 消息列表
            model: 模型名称

        Yields:
            逐块文本片段
        """
        url = f"{GROQ_API_URL}/chat/completions"
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
            "stream": True,
        }

        try:
            async with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    # SSE 格式: "data: {...}" 或 "data: [DONE]"
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]  # 去掉 "data: " 前缀
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
        except httpx.HTTPStatusError as e:
            print(f"[Groq] 流式 API 错误: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            print(f"[Groq] 流式请求失败: {e}")
            raise

    async def analyze_paper(self, title: str, abstract: str) -> dict:
        """使用 Groq 分析论文

        Args:
            title: 论文标题
            abstract: 论文摘要

        Returns:
            分析结果字典
        """
        prompt = PAPER_ANALYSIS_PROMPT.format(title=title, abstract=abstract)
        messages = [{"role": "user", "content": prompt}]

        try:
            response_text = await self.chat(messages)
            # 尝试解析 JSON
            # 有时 LLM 会在 JSON 前后加上额外文字，需要提取
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)

            # 如果没有找到 JSON，返回默认结构
            return {
                "summary": response_text[:200],
                "problems": [],
                "keywords": [],
                "methodology": "",
                "significance": "",
            }
        except json.JSONDecodeError as e:
            print(f"[Groq] JSON 解析失败: {e}")
            return {
                "summary": "",
                "problems": [],
                "keywords": [],
                "methodology": "",
                "significance": "",
            }
        except Exception as e:
            print(f"[Groq] 论文分析失败: {e}")
            return {
                "summary": "",
                "problems": [],
                "keywords": [],
                "methodology": "",
                "significance": "",
            }

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
