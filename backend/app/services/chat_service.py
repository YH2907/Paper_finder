"""对话服务 - Supabase 版本

管理对话的 CRUD 操作，并集成 AI 服务进行智能回复。
"""
import uuid
from typing import AsyncGenerator, Optional
from datetime import datetime

from app.services.ai.chat import DEFAULT_SYSTEM_PROMPT


class ChatService:
    """对话服务：管理对话的创建、消息处理，支持流式和非流式回复"""

    def __init__(self, db, ai_router=None):
        self.db = db
        self.ai_router = ai_router

    def get_chats(self, user_id) -> list[dict]:
        """获取用户的所有对话"""
        uid = str(user_id)
        chats = self.db.client.select('chats', user_id=uid, order='created_at.desc')

        result = []
        for chat in chats:
            # Get last message
            messages = self.db.client.select('messages', chat_id=chat['id'], order='created_at.desc', limit=1)
            last_message = messages[0]['content'] if messages else None

            result.append({
                "id": chat['id'],
                "title": chat['title'],
                "paper_id": chat.get('paper_id'),
                "created_at": chat['created_at'],
                "last_message": last_message,
            })

        return result

    def create_chat(self, user_id, title: str, paper_id=None) -> dict:
        """创建新对话"""
        chat_data = {
            'id': str(uuid.uuid4()),
            'user_id': str(user_id),
            'title': title,
        }
        if paper_id:
            chat_data['paper_id'] = str(paper_id)

        result = self.db.client.insert('chats', chat_data)
        chat = result[0]

        return {
            "id": chat['id'],
            "title": chat['title'],
            "paper_id": chat.get('paper_id'),
            "created_at": chat['created_at'],
            "messages": [],
        }

    def get_chat(self, chat_id, user_id) -> Optional[dict]:
        """获取对话详情（含消息列表）"""
        chats = self.db.client.select('chats', id=str(chat_id), user_id=str(user_id))
        if not chats:
            return None

        chat = chats[0]
        messages = self.db.client.select('messages', chat_id=chat['id'], order='created_at.asc')

        return {
            "id": chat['id'],
            "title": chat['title'],
            "paper_id": chat.get('paper_id'),
            "created_at": chat['created_at'],
            "messages": [
                {
                    "id": msg['id'],
                    "role": msg['role'],
                    "content": msg['content'],
                    "created_at": msg['created_at'],
                }
                for msg in messages
            ],
        }

    def save_user_message(self, chat_id, user_id, content: str):
        """保存用户消息"""
        msg_data = {
            'id': str(uuid.uuid4()),
            'chat_id': str(chat_id),
            'role': 'user',
            'content': content,
        }
        self.db.client.insert('messages', msg_data)

    def save_ai_message(self, chat_id, content: str):
        """保存 AI 回复消息"""
        msg_data = {
            'id': str(uuid.uuid4()),
            'chat_id': str(chat_id),
            'role': 'assistant',
            'content': content,
        }
        self.db.client.insert('messages', msg_data)

    def _build_system_prompt(self, chat_id) -> str:
        """构建系统提示词，如果对话关联论文则注入论文上下文"""
        prompt = DEFAULT_SYSTEM_PROMPT
        try:
            chats = self.db.client.select('chats', id=str(chat_id))
            if chats and chats[0].get('paper_id'):
                papers = self.db.client.select('papers', id=str(chats[0]['paper_id']))
                if papers:
                    p = papers[0]
                    title = p.get('title', '')
                    abstract = p.get('abstract', '') or ''
                    authors = p.get('authors') or []
                    if isinstance(authors, str):
                        authors_str = authors
                    else:
                        authors_str = ', '.join(authors[:5])
                    prompt += f"""

当前对话关联的论文上下文（用户的问题很可能是关于这篇论文的，请直接基于它回答，不要反问用户是哪篇论文）：
标题：{title}
作者：{authors_str}
摘要：{abstract[:2000]}"""
        except Exception as e:
            print(f"[ChatService] 加载论文上下文失败: {e}")
        return prompt

    async def chat_stream(self, chat_id, user_id, content: str) -> AsyncGenerator[str, None]:
        """流式对话"""
        # Save user message
        self.save_user_message(chat_id, user_id, content)

        # Get chat history
        messages = self.db.client.select('messages', chat_id=str(chat_id), order='created_at.asc')
        history = [{"role": m['role'], "content": m['content']} for m in messages]
        # 注入系统提示词（必须在最前面）
        history = [{"role": "system", "content": self._build_system_prompt(chat_id)}] + history

        # Get AI response
        if self.ai_router:
            full_response = ""
            async for chunk in self.ai_router.chat_stream(history):
                full_response += chunk
                yield chunk
            # Save AI response
            self.save_ai_message(chat_id, full_response)
        else:
            response = "AI 服务暂时不可用，请稍后再试。"
            self.save_ai_message(chat_id, response)
            yield response

    async def chat(self, chat_id, user_id, content: str) -> str:
        """非流式对话"""
        self.save_user_message(chat_id, user_id, content)

        messages = self.db.client.select('messages', chat_id=str(chat_id), order='created_at.asc')
        history = [{"role": m['role'], "content": m['content']} for m in messages]
        # 注入系统提示词（必须在最前面）
        history = [{"role": "system", "content": self._build_system_prompt(chat_id)}] + history

        if self.ai_router:
            response = await self.ai_router.chat(history)
        else:
            response = "AI 服务暂时不可用，请稍后再试。"

        self.save_ai_message(chat_id, response)
        return response

    def delete_chat(self, chat_id, user_id) -> bool:
        """删除对话"""
        chats = self.db.client.select('chats', id=str(chat_id), user_id=str(user_id))
        if not chats:
            return False
        # Delete messages first
        self.db.client.delete('messages', chat_id=str(chat_id))
        # Delete chat
        self.db.client.delete('chats', id=str(chat_id))
        return True
