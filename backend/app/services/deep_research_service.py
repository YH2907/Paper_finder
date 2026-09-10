"""深度研究服务 - Supabase 版本"""
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.services.crawler.engine import CrawlerEngine


class DeepResearchService:
    """深度研究服务"""

    def __init__(self, db, ai_router=None, paper_service=None):
        self.db = db
        self.ai_router = ai_router
        self.paper_service = paper_service

    async def deep_research(self, user_id, query: str, topic_id=None, limit: int = 20) -> dict:
        """分析研究问题并从学术数据源搜索相关论文."""
        analysis = await self._analyze_query(query)
        keywords = analysis["search_keywords"] or [query]

        engine = CrawlerEngine()
        try:
            papers = await engine.search_multi_query(
                keywords[:5], limit_per_query=max(1, min(limit, 10)),
                sources=["arxiv", "semantic_scholar", "openalex"],
                sort_by="relevance",
            )
        finally:
            await engine.close()

        papers = [self._paper_response(paper) for paper in papers[:limit]]
        return {
            "success": True,
            "analysis": analysis,
            "papers": papers,
            "total": len(papers),
            "message": "深度研究完成",
        }

    async def _analyze_query(self, query: str) -> dict:
        """让 AI 提取搜索词；AI 不可用时仍返回可搜索的结果."""
        fallback = {
            "main_concepts": [query],
            "research_objectives": [query],
            "key_problems": [query],
            "search_keywords": self._fallback_keywords(query),
            "summary": query,
        }
        if not self.ai_router:
            return fallback

        prompt = (
            "分析下面的研究问题，并且只返回 JSON。字段必须是："
            "main_concepts, research_objectives, key_problems, search_keywords, summary。"
            "所有数组字段都必须是字符串数组，search_keywords 使用英文或通用学术术语。\n"
            f"研究问题：{query}"
        )
        try:
            raw = await self.ai_router.chat([{"role": "user", "content": prompt}])
            parsed = self._parse_json(raw)
            if isinstance(parsed, dict):
                return {key: parsed.get(key, fallback[key]) for key in fallback}
        except Exception:
            pass
        return fallback

    @staticmethod
    def _parse_json(raw: str):
        """解析模型可能包裹在 markdown 代码块中的 JSON."""
        match = re.search(r"\{.*\}", raw or "", re.DOTALL)
        return json.loads(match.group(0) if match else raw)

    @staticmethod
    def _fallback_keywords(query: str) -> list[str]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}|[\u4e00-\u9fff]{2,}", query)
        return list(dict.fromkeys(words))[:5] or [query]

    @staticmethod
    def _paper_response(paper: dict) -> dict:
        return {
            "id": str(paper.get("id") or paper.get("doi") or uuid.uuid4()),
            "title": paper.get("title", ""),
            "authors": paper.get("authors", []),
            "abstract": paper.get("abstract", ""),
            "url": paper.get("url", ""),
            "source": paper.get("source", ""),
            "published_at": paper.get("published_at") or paper.get("published"),
            "doi": paper.get("doi"),
        }

    def create_research_session(self, user_id, query: str) -> dict:
        """创建研究会话"""
        data = {
            'id': str(uuid.uuid4()),
            'user_id': str(user_id),
            'query': query,
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        # Note: deep_research_sessions table not in schema, use chats instead
        chat_data = {
            'id': data['id'],
            'user_id': str(user_id),
            'title': f'深度研究: {query[:50]}',
        }
        result = self.db.client.insert('chats', chat_data)
        return {'session_id': result[0]['id'], 'status': 'pending'}

    def get_research_session(self, session_id, user_id) -> Optional[dict]:
        """获取研究会话"""
        chats = self.db.client.select('chats', id=str(session_id), user_id=str(user_id))
        if not chats:
            return None
        
        chat = chats[0]
        messages = self.db.client.select('messages', chat_id=chat['id'], order='created_at.asc')
        
        return {
            'session_id': chat['id'],
            'query': chat['title'].replace('深度研究: ', ''),
            'status': 'completed' if messages else 'pending',
            'messages': messages,
        }
