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

# 默认模型（llama 系列已从 Groq 下架，改用 qwen）
DEFAULT_MODEL = "groq/compound-mini"

# 已知可用的模型列表（用于自动纠正无效模型名）
VALID_MODELS = {
    "qwen/qwen3.8-27b",       # 当前可用，推荐
    "qwen/qwen3.6-27b",       # 当前可用（带 thinking）
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
    "groq/compound",
    "groq/compound-mini",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "allam-2-7b",
}

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
            model: 模型名称，默认为 groq/compound
        """
        # 自动纠正无效模型名（处理 Render Dashboard 旧环境变量）
        if model and model not in VALID_MODELS:
            print(f"[Groq] 警告: 模型 {model} 已下线，自动切换为 {DEFAULT_MODEL}")
            model = DEFAULT_MODEL
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
        # 只保留 system + 最近 10 条消息，避免历史累积拖慢响应
        messages = self._trim_messages(messages)
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        last_err = None
        for attempt in range(3):
            try:
                response = await self.client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                print(f"[Groq] API 错误: {status_code} - {e.response.text[:200]}")
                last_err = e
                # 429 限流 / 5xx 服务器错误：退避重试
                if status_code == 429 or status_code >= 500:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                raise
            except Exception as e:
                print(f"[Groq] 请求失败: {e}")
                last_err = e
                await asyncio.sleep(1.5 * (attempt + 1))
        raise last_err or RuntimeError("Groq AI 服务不可用")

    @staticmethod
    def _trim_messages(messages: list[dict], max_messages: int = 10) -> list[dict]:
        """保留 system 消息 + 最近 max_messages 条对话，控制上下文长度"""
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]
        return system_msgs + other_msgs[-max_messages:]

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
        messages = self._trim_messages(messages)
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
            "stream": True,
        }

        last_err = None
        for attempt in range(3):
            try:
                async with self.client.stream("POST", url, json=payload) as response:
                    # 注意：stream 模式下访问 response.text 前必须先 read()
                    if response.status_code != 200:
                        await response.aread()
                        body = response.text[:300]
                        print(f"[Groq] 流式 API 错误: {response.status_code} - {body}")
                        if response.status_code == 429 or response.status_code >= 500:
                            last_err = RuntimeError(f"Groq HTTP {response.status_code}: {body}")
                            await asyncio.sleep(1.5 * (attempt + 1))
                            continue
                        raise RuntimeError(f"Groq HTTP {response.status_code}: {body}")
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        # SSE 格式: "data: {...}" 或 "data: [DONE]"
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]  # 去掉 "data: " 前缀
                        if data_str.strip() == "[DONE]":
                            return
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                    return  # 正常结束
            except httpx.HTTPStatusError as e:
                print(f"[Groq] 流式 API 错误: {e.response.status_code}")
                last_err = e
                await asyncio.sleep(1.5 * (attempt + 1))
            except Exception as e:
                print(f"[Groq] 流式请求失败: {type(e).__name__}: {e}")
                last_err = e
                await asyncio.sleep(1.5 * (attempt + 1))
        raise last_err or RuntimeError("Groq AI 服务不可用")

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
