"""AI 服务路由器
优先使用 Groq（速度快、免费额度大），失败时降级到 Gemini。
支持结果缓存以减少重复请求。
支持流式输出。
"""
import hashlib
import json
import time
from typing import AsyncGenerator, Optional

from .base import BaseAIService


class AIRouter:
    """AI 服务路由器：主备切换 + 缓存"""

    def __init__(self, primary: BaseAIService, fallback: BaseAIService | None = None, cache_ttl: int = 3600):
        """初始化路由器"""
        self.primary = primary
        self.fallback = fallback
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[str, float]] = {}

    async def chat(self, messages: list[dict], model: str = None) -> str:
        """对话，优先 Groq，失败降级 Gemini"""
        cache_key = self._make_cache_key("chat", messages, model)
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            result = await self.primary.chat(messages, model)
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            print(f"[Router] 主服务（{type(self.primary).__name__}）失败: {e}")

        raise RuntimeError("Groq AI 服务不可用")

    async def chat_stream(self, messages: list[dict], model: str = None) -> AsyncGenerator[str, None]:
        """流式对话，优先主服务，失败降级备用服务"""
        try:
            async for chunk in self.primary.chat_stream(messages, model):
                yield chunk
        except Exception as e:
            print(f"[Router] Groq 流式服务失败: {e}")
            raise RuntimeError("Groq AI 服务不可用") from e

    async def analyze_paper(self, title: str, abstract: str) -> dict:
        """分析论文，优先 Groq，失败降级 Gemini"""
        cache_key = self._make_cache_key("analyze", {"title": title, "abstract": abstract})
        cached = self._get_cache(cache_key)
        if cached is not None:
            return json.loads(cached) if isinstance(cached, str) else cached

        try:
            result = await self.primary.analyze_paper(title, abstract)
            self._set_cache(cache_key, json.dumps(result, ensure_ascii=False))
            return result
        except Exception as e:
            print(f"[Router] 主服务分析失败: {e}")

        return {
            "summary": "",
            "problems": [],
            "keywords": [],
            "methodology": "",
            "significance": "",
        }

    def _make_cache_key(self, prefix: str, *args) -> str:
        content = json.dumps(args, sort_keys=True, ensure_ascii=False)
        hash_val = hashlib.md5(content.encode()).hexdigest()
        return f"{prefix}:{hash_val}"

    def _get_cache(self, key: str) -> Optional[str]:
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return value
            else:
                del self._cache[key]
        return None

    def _set_cache(self, key: str, value: str):
        self._cache[key] = (value, time.time())
        if len(self._cache) > 1000:
            self._clean_cache()

    def _clean_cache(self):
        now = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if now - timestamp >= self.cache_ttl
        ]
        for key in expired_keys:
            del self._cache[key]

    def clear_cache(self):
        self._cache.clear()

    async def close(self):
        await self.primary.close()
