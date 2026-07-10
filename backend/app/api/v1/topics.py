"""研究主题路由"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from app.api.v1.deps import get_current_user, get_topic_service
from app.models.user import User
from app.schemas.topic import TopicCreate, TopicUpdate, TopicResponse
from app.schemas.common import ResponseBase
from app.services.topic_service import TopicService

router = APIRouter(prefix="/topics", tags=["研究主题"])


async def _trigger_realtime_recommendation(user_id: uuid.UUID) -> None:
    """主题变更后，后台触发一次实时推荐。"""
    from app.services.scheduler_service import scheduler

    await scheduler.trigger_push(user_id, trigger_reason="topic-updated")


@router.get("/", response_model=ResponseBase[list[TopicResponse]])
async def get_topics(
    current_user: User = Depends(get_current_user),
    topic_service: TopicService = Depends(get_topic_service),
):
    """
    获取当前用户的所有研究主题

    返回用户创建的所有研究主题列表
    """
    topics = topic_service.get_topics_by_user(current_user.id)
    return ResponseBase(success=True, data=topics)


@router.post("/", response_model=ResponseBase[TopicResponse], status_code=status.HTTP_201_CREATED)
async def create_topic(
    topic_in: TopicCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    topic_service: TopicService = Depends(get_topic_service),
):
    """
    创建研究主题

    - **name**: 主题名称
    - **keywords**: 关键词列表
    - **exclude_keywords**: 排除关键词（可选）
    - **description**: 主题描述（可选）
    - **problem_statement**: 问题陈述（可选）
    """
    topic = topic_service.create_topic(
        user_id=current_user.id,
        name=topic_in.name,
        keywords=topic_in.keywords,
        exclude_keywords=topic_in.exclude_keywords,
        description=topic_in.description,
        problem_statement=topic_in.problem_statement,
    )
    background_tasks.add_task(_trigger_realtime_recommendation, current_user.id)
    return ResponseBase(success=True, data=topic, message="主题创建成功")


@router.get("/{topic_id}", response_model=ResponseBase[TopicResponse])
async def get_topic(
    topic_id: str,
    current_user: User = Depends(get_current_user),
    topic_service: TopicService = Depends(get_topic_service),
):
    """
    获取研究主题详情

    - **topic_id**: 主题ID
    """
    try:
        topic_uuid = uuid.UUID(topic_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的主题ID格式",
        )

    topic = topic_service.get_topic_by_id(topic_uuid, current_user.id)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="主题不存在",
        )
    return ResponseBase(success=True, data=topic)


@router.put("/{topic_id}", response_model=ResponseBase[TopicResponse])
async def update_topic(
    topic_id: str,
    topic_in: TopicUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    topic_service: TopicService = Depends(get_topic_service),
):
    """
    更新研究主题

    - **topic_id**: 主题ID
    - 支持部分更新
    """
    try:
        topic_uuid = uuid.UUID(topic_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的主题ID格式",
        )

    topic = topic_service.get_topic_by_id(topic_uuid, current_user.id)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="主题不存在",
        )

    updated_topic = topic_service.update_topic(
        topic,
        name=topic_in.name,
        keywords=topic_in.keywords,
        exclude_keywords=topic_in.exclude_keywords,
        description=topic_in.description,
        problem_statement=topic_in.problem_statement,
        is_active=topic_in.is_active,
    )
    background_tasks.add_task(_trigger_realtime_recommendation, current_user.id)
    return ResponseBase(success=True, data=updated_topic, message="主题更新成功")


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    topic_service: TopicService = Depends(get_topic_service),
):
    """
    删除研究主题

    - **topic_id**: 主题ID
    """
    try:
        topic_uuid = uuid.UUID(topic_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的主题ID格式",
        )

    topic = topic_service.get_topic_by_id(topic_uuid, current_user.id)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="主题不存在",
        )

    topic_service.delete_topic(topic)
    background_tasks.add_task(_trigger_realtime_recommendation, current_user.id)
