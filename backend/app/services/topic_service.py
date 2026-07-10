"""主题服务"""

from typing import Optional
import uuid
from sqlalchemy.orm import Session, joinedload

from app.models.topic import Topic
from app.models.paper import Paper
from app.models.user_paper import UserPaper


class TopicService:
    """主题服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_topics_by_user(self, user_id: uuid.UUID) -> list[Topic]:
        """获取用户的所有主题"""
        return self.db.query(Topic).filter(Topic.user_id == user_id).all()
    
    def get_topic_by_id(self, topic_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Topic]:
        """获取主题详情"""
        return self.db.query(Topic).filter(
            Topic.id == topic_id,
            Topic.user_id == user_id,
        ).first()
    
    def create_topic(
        self,
        user_id: uuid.UUID,
        name: str,
        keywords: list[str],
        exclude_keywords: list[str] = None,
        description: str = None,
        problem_statement: str = None,
    ) -> Topic:
        """创建主题"""
        topic = Topic(
            user_id=user_id,
            name=name,
            keywords=keywords,
            exclude_keywords=exclude_keywords or [],
            description=description,
            problem_statement=problem_statement,
            is_active=True,
        )
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)
        return topic
    
    def update_topic(
        self,
        topic: Topic,
        name: str = None,
        keywords: list[str] = None,
        exclude_keywords: list[str] = None,
        description: str = None,
        problem_statement: str = None,
        is_active: bool = None,
    ) -> Topic:
        """更新主题"""
        if name is not None:
            topic.name = name
        if keywords is not None:
            topic.keywords = keywords
        if exclude_keywords is not None:
            topic.exclude_keywords = exclude_keywords
        if description is not None:
            topic.description = description
        if problem_statement is not None:
            topic.problem_statement = problem_statement
        if is_active is not None:
            topic.is_active = is_active
        
        self.db.commit()
        self.db.refresh(topic)
        return topic
    
    def _normalize_keywords(self, keywords: list[str]) -> set[str]:
        """标准化关键词，统一小写并移除空白项。"""
        result: set[str] = set()
        for kw in keywords or []:
            cleaned = (kw or "").strip().lower()
            if cleaned:
                result.add(cleaned)
        return result

    def _paper_text(self, paper: Paper) -> str:
        return f"{paper.title or ''} {paper.abstract or ''}".lower()

    def delete_topic(self, topic: Topic):
        """删除主题，并清理该主题相关的用户论文关联。"""
        user_id = topic.user_id
        deleted_keywords = self._normalize_keywords(topic.keywords)

        # 先删除主题
        self.db.delete(topic)
        self.db.flush()

        # 计算用户剩余活跃主题关键词
        remaining_topics = (
            self.db.query(Topic)
            .filter(Topic.user_id == user_id, Topic.is_active == True)
            .all()
        )
        remaining_keywords: set[str] = set()
        for t in remaining_topics:
            remaining_keywords.update(self._normalize_keywords(t.keywords))

        # 仅删除“匹配被删主题关键词且不再匹配其他主题关键词”的用户论文关联
        user_papers = (
            self.db.query(UserPaper)
            .options(joinedload(UserPaper.paper))
            .filter(UserPaper.user_id == user_id)
            .all()
        )

        delete_ids: list[uuid.UUID] = []
        for up in user_papers:
            text = self._paper_text(up.paper)
            matches_deleted = any(kw in text for kw in deleted_keywords) if deleted_keywords else False
            matches_remaining = any(kw in text for kw in remaining_keywords) if remaining_keywords else False
            if matches_deleted and not matches_remaining:
                delete_ids.append(up.id)

        if delete_ids:
            self.db.query(UserPaper).filter(UserPaper.id.in_(delete_ids)).delete(synchronize_session=False)

        self.db.commit()
