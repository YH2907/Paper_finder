"""Google Gemini AI 服务实现

使用 Google Gemini API 进行 LLM 对话
文档: https://ai.google.dev/api/rest
"""
import asyncio
import json
from typing import AsyncGenerator, Optional

import httpx
from .base import BaseAIService

# Gemini API 地址
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# 默认模型
DEFAULT_MODEL = "gemini-1.5-flash"

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


class GeminiService(BaseAIService):
    """Google Gemini AI 服务"""

    def __init__(self, api_key: str, model: str = None):
        """初始化 Gemini 服务

        Args:
            api_key: Google API 密钥
            model: 模型名称，默认为 gemini-1.5-flash
        """
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(self, messages: list[dict], model: str = None) -> str:
        """与 Gemini LLM 对话

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            model: 模型名称，为 None 时使用默认模型

        Returns:
            AI 回复文本
        """
        current_model = model or self.model
        url = f"{GEMINI_API_BASE}/models/{current_model}:generateContent"

        # 将 OpenAI 格式的消息转为 Gemini 格式
        gemini_contents = self._convert_messages(messages)

        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            },
        }

        params = {"key": self.api_key}
        try:
            response = await self.client.post(url, json=payload, params=params)
            response.raise_for_status()
            data = response.json()

            # 提取回复文本
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()

            return ""
        except httpx.HTTPStatusError as e:
            print(f"[Gemini] API 错误: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            print(f"[Gemini] 请求失败: {e}")
            raise

    async def chat_stream(
        self, messages: list[dict], model: str = None
    ) -> AsyncGenerator[str, None]:
        """流式对话 — 逐 token 返回 AI 回复

        使用 Gemini 的 streamGenerateContent 接口。

        Args:
            messages: 消息列表
            model: 模型名称

        Yields:
            逐块文本片段
        """
        current_model = model or self.model
        url = f"{GEMINI_API_BASE}/models/{current_model}:streamGenerateContent"

        gemini_contents = self._convert_messages(messages)

        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            },
        }

        params = {"key": self.api_key, "alt": "sse"}

        try:
            async with self.client.stream(
                "POST", url, json=payload, params=params
            ) as response:
                response.raise_for_status()
                # Gemini SSE 格式: 每行是一个 JSON chunk
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    # 按换行分割，逐行解析
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        # 去掉 "data: " 前缀（如有）
                        if line.startswith("data: "):
                            line = line[6:]
                        try:
                            data = json.loads(line)
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                text = parts[0].get("text", "") if parts else ""
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPStatusError as e:
            print(f"[Gemini] 流式 API 错误: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            print(f"[Gemini] 流式请求失败: {e}")
            raise

    async def analyze_paper(self, title: str, abstract: str) -> dict:
        """使用 Gemini 分析论文

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
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)

            return {
                "summary": response_text[:200],
                "problems": [],
                "keywords": [],
                "methodology": "",
                "significance": "",
            }
        except json.JSONDecodeError as e:
            print(f"[Gemini] JSON 解析失败: {e}")
            return {
                "summary": "",
                "problems": [],
                "keywords": [],
                "methodology": "",
                "significance": "",
            }
        except Exception as e:
            print(f"[Gemini] 论文分析失败: {e}")
            return {
                "summary": "",
                "problems": [],
                "keywords": [],
                "methodology": "",
                "significance": "",
            }

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """将 OpenAI 格式消息转为 Gemini 格式

        Gemini 的角色只有 "user" 和 "model"，需要做转换。

        Args:
            messages: OpenAI 格式消息列表

        Returns:
            Gemini 格式内容列表
        """
        gemini_contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Gemini 使用 "model" 而不是 "assistant"
            if role == "assistant":
                role = "model"

            gemini_contents.append({
                "role": role,
                "parts": [{"text": content}],
            })

        return gemini_contents

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
