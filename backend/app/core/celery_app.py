"""Celery 异步任务配置"""

from celery import Celery

from app.config import settings

# 创建 Celery 应用
celery_app = Celery(
    "paper_finder",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery 配置
celery_app.conf.update(
    # 序列化方式
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 任务结果过期时间（秒）
    result_expires=3600,
    # 任务路由
    task_routes={
        "app.tasks.paper_search.*": {"queue": "search"},
        "app.tasks.paper_analyze.*": {"queue": "analyze"},
        "app.tasks.notify.*": {"queue": "notify"},
    },
    # 任务限速
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
)

# 自动发现任务模块
celery_app.autodiscover_tasks(["app.tasks"])
