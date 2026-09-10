"""对话服务

管理多轮对话，维护对话历史。
"""

import uuid
from typing import Optional

from .router import AIRouter


class ChatSession:
    """对话会话"""

    def __init__(self, session_id: str = None, system_prompt: str = None):
        """初始化对话会话

        Args:
            session_id: 会话 ID，为 None 时自动生成
            system_prompt: 系统提示词
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.messages: list[dict] = []

        # 设置系统提示
        if system_prompt:
            self.messages.append({
                "role": "system",
                "content": system_prompt,
            })

    def add_message(self, role: str, content: str):
        """添加消息到对话历史

        Args:
            role: 角色，"user" 或 "assistant"
            content: 消息内容
        """
        self.messages.append({
            "role": role,
            "content": content,
        })

    def get_messages(self) -> list[dict]:
        """获取对话历史

        Returns:
            消息列表
        """
        return self.messages

    def clear(self):
        """清空对话历史（保留系统提示）"""
        system_msg = None
        if self.messages and self.messages[0]["role"] == "system":
            system_msg = self.messages[0]
        self.messages = []
        if system_msg:
            self.messages.append(system_msg)


# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """你是一个学术论文助手，用中文回答用户关于学术研究的问题。

回答规则：
1. 用自然、简洁的段落回答，像正常聊天一样。
2. 不要使用 markdown 格式符号（不要用 ###、**、- 列表等），因为界面不渲染 markdown，这些符号会直接显示出来很难看。
3. 不要主动罗列论文或给出论文链接。只有当用户明确要求推荐论文时，才简要提及论文标题。
4. 回答控制在合理长度内，直接回答问题，不要长篇大论。"""


class ChatService:
    """对话服务：管理多轮对话"""

    def __init__(self, ai_router: AIRouter, max_history: int = 20):
        """初始化对话服务

        Args:
            ai_router: AI 路由器实例
            max_history: 最大历史消息数（不含系统提示）
        """
        self.ai_router = ai_router
        self.max_history = max_history
        # 会话存储: {session_id: ChatSession}
        self._sessions: dict[str, ChatSession] = {}

    async def chat(
        self,
        message: str,
        session_id: str = None,
        system_prompt: str = None,
    ) -> dict:
        """进行对话

        Args:
            message: 用户消息
            session_id: 会话 ID，为 None 时创建新会话
            system_prompt: 系统提示词，仅新会话时使用

        Returns:
            包含 session_id 和 reply 的字典
        """
        # 获取或创建会话
        session = self._get_or_create_session(session_id, system_prompt)

        # 添加用户消息
        session.add_message("user", message)

        # 裁剪历史消息（保留系统提示）
        self._trim_history(session)

        # 调用 AI 服务
        try:
            reply = await self.ai_router.chat(session.get_messages())
            session.add_message("assistant", reply)
            return {
                "session_id": session.session_id,
                "reply": reply,
            }
        except Exception as e:
            # 移除失败的用户消息
            if session.messages and session.messages[-1]["role"] == "user":
                session.messages.pop()
            raise e

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取对话会话

        Args:
            session_id: 会话 ID

        Returns:
            对话会话，不存在返回 None
        """
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """删除对话会话

        Args:
            session_id: 会话 ID

        Returns:
            是否成功删除
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[str]:
        """列出所有会话 ID

        Returns:
            会话 ID 列表
        """
        return list(self._sessions.keys())

    def _get_or_create_session(
        self, session_id: str = None, system_prompt: str = None
    ) -> ChatSession:
        """获取已有会话或创建新会话

        Args:
            session_id: 会话 ID
            system_prompt: 系统提示词

        Returns:
            对话会话实例
        """
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]

        # 创建新会话
        prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        session = ChatSession(session_id=session_id, system_prompt=prompt)
        self._sessions[session.session_id] = session
        return session

    def _trim_history(self, session: ChatSession):
        """裁剪对话历史，保留最新的消息

        Args:
            session: 对话会话
        """
        messages = session.messages
        if len(messages) <= 1:
            return

        # 检查是否有系统提示
        has_system = messages[0]["role"] == "system"
        system_msg = messages[0] if has_system else None

        # 获取非系统消息
        non_system = messages[1:] if has_system else messages

        # 裁剪到最大长度
        if len(non_system) > self.max_history:
            non_system = non_system[-self.max_history:]

        # 重建消息列表
        if system_msg:
            session.messages = [system_msg] + non_system
        else:
            session.messages = non_system
