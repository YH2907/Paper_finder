"""调度服务 - Supabase 版本

提供定时推送调度器。
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class SchedulerService:
    """后台调度器，定时推送论文"""

    def __init__(self):
        self._task = None
        self._running = False

    async def start(self):
        """启动调度器"""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("📅 Scheduler started")

    async def stop(self):
        """停止调度器"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("📅 Scheduler stopped")

    async def trigger_push(self, user_id, trigger_reason: str = "manual"):
        """手动触发推送"""
        try:
            from app.core.database import get_db, USE_SUPABASE
            gen = get_db()
            db = next(gen)
            from app.services.recommendation_service import RecommendationService
            from app.services.notification_service import NotificationService

            rec_svc = RecommendationService(db)
            notif_svc = NotificationService(db)

            papers = rec_svc.get_recommendations_for_user(user_id, limit=10)
            if papers:
                count = rec_svc.push_papers_to_user(user_id, papers)
                notif_svc.create_notification(
                    user_id=user_id,
                    title='新论文推荐',
                    content=f'为您推荐了 {count} 篇新论文（触发: {trigger_reason}）',
                    type='recommendation',
                )
                logger.info(f"📤 Pushed {count} papers to user {user_id}")
        except Exception as e:
            logger.error(f"Push failed: {e}")

    async def _run_loop(self):
        """主循环：每小时检查一次是否需要推送"""
        while self._running:
            try:
                await self._check_and_push()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(3600)  # Check every hour

    async def _check_and_push(self):
        """检查并推送"""
        try:
            from app.core.database import get_db, USE_SUPABASE
            gen = get_db()
            db = next(gen)

            users = db.client.select('users')
            now = datetime.now(timezone.utc)

            from app.services.recommendation_service import RecommendationService
            from app.services.notification_service import NotificationService

            rec_svc = RecommendationService(db)
            notif_svc = NotificationService(db)

            for user in users:
                if not user.get('is_active', True):
                    continue
                push_enabled = user.get('push_enabled', True)
                if not push_enabled:
                    continue

                papers = rec_svc.get_recommendations_for_user(user['id'], limit=10)
                if papers:
                    count = rec_svc.push_papers_to_user(user['id'], papers)
                    if count > 0:
                        notif_svc.create_notification(
                            user_id=user['id'],
                            title='新论文推荐',
                            content=f'为您推荐了 {count} 篇新论文',
                            type='recommendation',
                        )
                        logger.info(f"📤 Auto-pushed {count} papers to user {user['id']}")
        except Exception as e:
            logger.error(f"Check and push error: {e}")


# Module-level singleton
scheduler = SchedulerService()
