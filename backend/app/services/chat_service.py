"""对话服务 - 数据库版本

管理对话的 CRUD 操作，并集成 AI 服务进行智能回复。
"""
import uuid
from typing import AsyncGenerator, Optional

from sqlalchemy import select, desc
from sqlalchemy.orm import Session, joinedload
from app.models.chat import Chat
from app.models.message import Message
from app.models.paper import Paper
from app.services.ai.chat import DEFAULT_SYSTEM_PROMPT


class ChatService:
    """对话服务：管理对话的创建、消息处理，支持流式和非流式回复"""

    def __init__(self, db: Session, ai_router=None):
        """初始化对话服务

        Args:
            db: 数据库会话
            ai_router: AI 路由器实例（可选，用于生成 AI 回复）
        """
        self.db = db
        self.ai_router = ai_router

    def get_chats(self, user_id: uuid.UUID) -> list[dict]:
        """获取用户的所有对话

        Args:
            user_id: 用户 ID

        Returns:
            对话列表（含最后一条消息）
        """
        stmt = (
            select(Chat)
            .where(Chat.user_id == user_id)
            .options(joinedload(Chat.messages))
            .order_by(desc(Chat.created_at))
        )
        result = self.db.execute(stmt).unique().scalars().all()

        chats = []
        for chat in result:
            last_message = None
            if chat.messages:
                # 获取最后一条消息
                sorted_msgs = sorted(chat.messages, key=lambda m: m.created_at)
                last_message = sorted_msgs[-1].content if sorted_msgs else None

            chats.append({
                "id": chat.id,
                "title": chat.title,
                "paper_id": chat.paper_id,
                "created_at": chat.created_at,
                "last_message": last_message,
            })

        return chats

    def create_chat(
        self,
        user_id: uuid.UUID,
        title: str,
        paper_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """创建新对话

        Args:
            user_id: 用户 ID
            title: 对话标题
            paper_id: 关联的论文 ID（可选）

        Returns:
            创建的对话信息
        """
        chat = Chat(
            user_id=user_id,
            title=title,
            paper_id=paper_id,
        )
        self.db.add(chat)
        self.db.commit()
        self.db.refresh(chat)

        return {
            "id": chat.id,
            "title": chat.title,
            "paper_id": chat.paper_id,
            "created_at": chat.created_at,
            "messages": [],
        }

    def get_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> Optional[dict]:
        """获取对话详情（含消息列表）

        Args:
            chat_id: 对话 ID
            user_id: 用户 ID（用于权限验证）

        Returns:
            对话详情，不存在或无权限返回 None
        """
        stmt = (
            select(Chat)
            .where(Chat.id == chat_id, Chat.user_id == user_id)
            .options(joinedload(Chat.messages))
        )
        result = self.db.execute(stmt).unique().scalar_one_or_none()

        if not result:
            return None

        messages = sorted(result.messages, key=lambda m: m.created_at)

        return {
            "id": result.id,
            "title": result.title,
            "paper_id": result.paper_id,
            "created_at": result.created_at,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at,
                }
                for msg in messages
            ],
        }

    # ──────────────────── 流式对话支持方法 ────────────────────

    def save_user_message(
        self, chat_id: uuid.UUID, user_id: uuid.UUID, content: str
    ) -> Optional[dict]:
        """验证对话权限并保存用户消息

        Args:
            chat_id: 对话 ID
            user_id: 用户 ID
            content: 消息内容

        Returns:
            保存的消息信息，对话不存在或无权限返回 None
        """
        stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        chat = self.db.execute(stmt).scalar_one_or_none()

        if not chat:
            return None

        user_message = Message(
            chat_id=chat_id,
            role="user",
            content=content,
        )
        self.db.add(user_message)
        self.db.commit()
        self.db.refresh(user_message)

        return {
            "id": user_message.id,
            "role": user_message.role,
            "content": user_message.content,
            "created_at": user_message.created_at,
        }

    def build_ai_messages(self, chat_id: uuid.UUID) -> list[dict]:
        """构建发送给 AI 的消息列表（含历史上下文）

        Args:
            chat_id: 对话 ID

        Returns:
            AI 消息格式列表
        """
        messages = []

        # 构建系统提示
        system_prompt = DEFAULT_SYSTEM_PROMPT

        # 获取对话对象，检查是否关联了论文
        stmt = select(Chat).where(Chat.id == chat_id)
        chat = self.db.execute(stmt).scalar_one_or_none()
        if chat and chat.paper_id:
            paper_stmt = select(Paper).where(Paper.id == chat.paper_id)
            paper = self.db.execute(paper_stmt).scalar_one_or_none()
            if paper:
                system_prompt += (
                    f"\n\n当前正在讨论的论文：\n"
                    f"标题：{paper.title}\n"
                    f"摘要：{paper.abstract}"
                )

        messages.append({"role": "system", "content": system_prompt})

        # 加载历史消息（最近 20 条）
        history_stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at)
        )
        history = self.db.execute(history_stmt).scalars().all()

        for msg in history[-20:]:
            messages.append({"role": msg.role, "content": msg.content})

        return messages

    async def stream_ai_reply(
        self, messages: list[dict]
    ) -> AsyncGenerator[str, None]:
        """通过 AI 路由器流式获取回复

        Args:
            messages: AI 消息列表

        Yields:
            逐块文本片段

        Raises:
            RuntimeError: 所有 AI 服务不可用时
        """
        if not self.ai_router:
            yield "AI 服务尚未配置。请配置 AI 服务以获取智能回复。"
            return

        async for chunk in self.ai_router.chat_stream(messages):
            yield chunk

    def save_assistant_message(self, chat_id: uuid.UUID, content: str) -> dict:
        """保存 AI 回复消息

        Args:
            chat_id: 对话 ID
            content: 回复内容

        Returns:
            保存的消息信息
        """
        assistant_message = Message(
            chat_id=chat_id,
            role="assistant",
            content=content,
        )
        self.db.add(assistant_message)
        self.db.commit()
        self.db.refresh(assistant_message)

        return {
            "id": assistant_message.id,
            "role": assistant_message.role,
            "content": assistant_message.content,
            "created_at": assistant_message.created_at,
        }

    # ──────────────────── 非流式对话（原有方法） ────────────────────

    async def send_message(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
    ) -> Optional[dict]:
        """发送消息并获取 AI 回复（非流式）

        Args:
            chat_id: 对话 ID
            user_id: 用户 ID（用于权限验证）
            content: 消息内容

        Returns:
            包含 AI 回复的消息信息，对话不存在返回 None
        """
        # 验证对话存在且属于当前用户
        stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        chat = self.db.execute(stmt).scalar_one_or_none()

        if not chat:
            return None

        # 保存用户消息
        user_message = Message(
            chat_id=chat_id,
            role="user",
            content=content,
        )
        self.db.add(user_message)
        self.db.commit()
        self.db.refresh(user_message)

        # 如果有 AI 路由器，生成 AI 回复
        if self.ai_router:
            # 构建对话历史
            ai_messages = self.build_ai_messages(chat_id)

            try:
                ai_reply = await self.ai_router.chat(ai_messages)

                # 保存 AI 回复
                assistant_message = Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=ai_reply,
                )
                self.db.add(assistant_message)
                self.db.commit()
                self.db.refresh(assistant_message)

                return {
                    "id": assistant_message.id,
                    "role": assistant_message.role,
                    "content": assistant_message.content,
                    "created_at": assistant_message.created_at,
                }
            except Exception as e:
                # AI 回复失败时返回错误提示
                error_message = Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=f"抱歉，AI 服务暂时不可用。错误信息：{str(e)}",
                )
                self.db.add(error_message)
                self.db.commit()
                self.db.refresh(error_message)

                return {
                    "id": error_message.id,
                    "role": error_message.role,
                    "content": error_message.content,
                    "created_at": error_message.created_at,
                }
        else:
            # 没有 AI 服务时返回提示
            no_ai_message = Message(
                chat_id=chat_id,
                role="assistant",
                content="AI 服务尚未配置。请配置 AI 服务以获取智能回复。",
            )
            self.db.add(no_ai_message)
            self.db.commit()
            self.db.refresh(no_ai_message)

            return {
                "id": no_ai_message.id,
                "role": no_ai_message.role,
                "content": no_ai_message.content,
                "created_at": no_ai_message.created_at,
            }

    # ──────────────────── 流式对话方法 ────────────────────

    async def send_message_stream(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
    ) -> AsyncGenerator[str, None]:
        """发送消息并获取 AI 回复（流式 SSE）

        Args:
            chat_id: 对话 ID
            user_id: 用户 ID
            content: 消息内容

        Yields:
            SSE 格式的事件字符串
        """
        import json

        # 验证对话
        stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        chat = self.db.execute(stmt).scalar_one_or_none()
        if not chat:
            yield f"data: {json.dumps({'type': 'error', 'content': '对话不存在'})}\n\n"
            return

        # 保存用户消息
        user_msg = Message(chat_id=chat_id, role="user", content=content)
        self.db.add(user_msg)
        self.db.commit()

        # 构建 AI 消息
        messages = self._build_ai_messages_for_stream(chat_id, chat)

        if not self.ai_router:
            error_msg = "AI 服务尚未配置"
            yield f"data: {json.dumps({'type': 'token', 'content': error_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': error_msg})}\n\n"
            return

        # 流式获取 AI 回复
        full_reply = ""
        try:
            async for chunk in self.ai_router.chat_stream(messages):
                full_reply += chunk
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
        except Exception as e:
            error_msg = f"AI 服务错误: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
            full_reply = error_msg

        # 保存 AI 回复
        ai_msg = Message(chat_id=chat_id, role="assistant", content=full_reply)
        self.db.add(ai_msg)
        self.db.commit()

        yield f"data: {json.dumps({'type': 'done', 'content': full_reply, 'message_id': str(ai_msg.id)})}\n\n"

    def _build_ai_messages_for_stream(self, chat_id: uuid.UUID, chat: Chat) -> list[dict]:
        """构建流式对话的 AI 消息列表"""
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at)
            .limit(20)
        )
        history = self.db.execute(stmt).scalars().all()

        messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        return messages

    def delete_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """删除对话

        Args:
            chat_id: 对话 ID
            user_id: 用户 ID（用于权限验证）

        Returns:
            是否成功删除
        """
        stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        chat = self.db.execute(stmt).scalar_one_or_none()

        if not chat:
            return False

        self.db.delete(chat)
        self.db.commit()
        return True

    def _build_ai_messages(self, history: list[Message], chat: Chat) -> list[dict]:
        """构建发送给 AI 的消息列表

        Args:
            history: 历史消息列表
            chat: 对话对象

        Returns:
            AI 消息格式列表
        """
        messages = []

        # 构建系统提示
        system_prompt = DEFAULT_SYSTEM_PROMPT

        # 如果关联了论文，在系统提示中加入论文信息
        if chat.paper_id:
            stmt = select(Paper).where(Paper.id == chat.paper_id)
            paper = self.db.execute(stmt).scalar_one_or_none()
            if paper:
                system_prompt += (
                    f"\n\n当前正在讨论的论文：\n"
                    f"标题：{paper.title}\n"
                    f"摘要：{paper.abstract}"
                )

        messages.append({"role": "system", "content": system_prompt})

        # 添加历史消息（最近 20 条）
        for msg in history[-20:]:
            messages.append({"role": msg.role, "content": msg.content})

        return messages
