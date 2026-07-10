"""定时推送调度服务

基于 APScheduler 实现定时任务调度，支持按用户配置的频率推送论文。
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.config import settings
from app.models.user import User
from app.models.topic import Topic
from app.models.notification import Notification

# 配置日志
logger = logging.getLogger("scheduler")


class SchedulerService:
    """定时推送调度服务"""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_trigger_minute: dict[uuid.UUID, str] = {}
        self._timezone = ZoneInfo(settings.APP_TIMEZONE)

    async def start(self):
        """启动调度器"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("⏰ 论文推送调度器已启动")

    async def stop(self):
        """停止调度器"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("⏰ 论文推送调度器已停止")

    async def _run_loop(self):
        """主调度循环，每分钟检查一次"""
        while self._running:
            try:
                now = datetime.now(self._timezone)
                current_time = f"{now.hour:02d}:{now.minute:02d}"
                current_day = now.isoweekday()  # 1=Monday, 7=Sunday
                current_date = now.day

                db = SessionLocal()
                try:
                    # 查询所有启用推送的用户
                    users = db.query(User).filter(User.push_enabled == True).all()

                    if users:
                        logger.debug(f"[调度器] 检查 {len(users)} 个用户的推送配置, 当前时间: {current_time}")

                    for user in users:
                        should_push = False

                        if user.push_frequency == "daily":
                            # 每天：匹配时间
                            should_push = user.push_time == current_time
                        elif user.push_frequency == "weekly":
                            # 每周：匹配周一和时间
                            should_push = current_day == 1 and user.push_time == current_time
                        elif user.push_frequency == "monthly":
                            # 每月：匹配每月1号和时间
                            should_push = current_date == 1 and user.push_time == current_time

                        if should_push:
                            minute_key = now.strftime("%Y-%m-%dT%H:%M")
                            if self._last_trigger_minute.get(user.id) == minute_key:
                                logger.debug(f"[调度器] 用户 {user.name} 本分钟已触发过，跳过")
                                continue
                            self._last_trigger_minute[user.id] = minute_key
                            logger.info(f"[调度器] 触发用户 {user.name} 的定时推送 (频率: {user.push_frequency})")
                            await self._push_papers(db, user, trigger_reason="scheduled")
                finally:
                    db.close()

            except Exception as e:
                logger.error(f"❌ 调度器错误: {e}", exc_info=True)

            # 等待60秒
            await asyncio.sleep(60)

    async def _push_papers(self, db: Session, user: User, trigger_reason: str = "manual"):
        """为用户推送论文推荐
        
        如果用户有定义了 problem_statement 的主题，使用 Agent 服务进行问题驱动的搜索。
        否则，使用推荐服务进行关键词搜索。
        """
        try:
            logger.info(f"[推送] 开始为用户 {user.name} 搜索论文 (trigger={trigger_reason})")
            
            # 检查用户是否有定义了问题陈述的主题
            topics = (
                db.query(Topic)
                .filter(Topic.user_id == user.id, Topic.is_active == True)
                .all()
            )
            
            has_problems = any(t.problem_statement for t in topics)
            
            if has_problems and settings.has_ai_configured:
                # 使用 Agent 服务进行问题驱动的搜索
                from app.services.agent_service import AgentService
                from app.services.ai.router import AIRouter
                from app.services.ai.groq import GroqService
                from app.services.ai.gemini import GeminiService
                
                # 创建 AI 路由器
                ai_router = None
                if settings.GROQ_API_KEY and settings.GEMINI_API_KEY:
                    primary = GroqService(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
                    fallback = GeminiService(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
                    ai_router = AIRouter(primary=primary, fallback=fallback)
                elif settings.GROQ_API_KEY:
                    from app.services.ai.groq import GroqService
                    ai_router = GroqService(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
                elif settings.GEMINI_API_KEY:
                    from app.services.ai.gemini import GeminiService
                    ai_router = GeminiService(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
                
                agent = AgentService(db=db, ai_router=ai_router)
                papers = await agent.search_and_push(
                    user_id=user.id,
                    limit=user.push_count,
                )
                
                # 关闭 AI 路由器
                if ai_router:
                    await ai_router.close()
                    
                if papers:
                    logger.info(f"[推送] Agent 为用户 {user.name} 推送 {len(papers)} 篇论文")
                else:
                    logger.info(f"[推送] Agent 没有为用户 {user.name} 找到相关论文")
                    
            else:
                # 使用推荐服务进行关键词搜索
                from app.services.crawler.engine import CrawlerEngine
                from app.services.recommendation_service import RecommendationService

                crawler = CrawlerEngine(ieee_api_key=settings.IEEE_API_KEY)
                try:
                    rec_service = RecommendationService(db=db, crawler_engine=crawler)
                    recommended_papers = await rec_service.fetch_and_recommend(
                        user_id=user.id,
                        limit=user.push_count,
                        force_online=True,
                        only_unseen=True,
                    )
                finally:
                    await crawler.close()

                papers_to_push = recommended_papers[:user.push_count]

                if not papers_to_push:
                    logger.info(f"[推送] 用户 {user.name} 没有新论文可推送")
                    return

                # 创建通知
                paper_titles = [f"• {p.title}" for p in papers_to_push[:5]]
                content_lines = [f"根据您的研究主题，为您推荐 {len(papers_to_push)} 篇论文："]
                content_lines.extend(paper_titles)
                if len(papers_to_push) > 5:
                    content_lines.append(f"...等共 {len(papers_to_push)} 篇")

                notification = Notification(
                    user_id=user.id,
                    title=f"📚 论文推荐 - {len(papers_to_push)} 篇新论文",
                    content="\n".join(content_lines),
                    type="paper",
                    is_read=False,
                )
                db.add(notification)
                db.commit()

                logger.info(
                    f"📬 已为用户 {user.name} 推送 {len(papers_to_push)} 篇论文"
                    f" (trigger={trigger_reason})"
                )

        except Exception as e:
            logger.error(f"❌ 推送失败 (用户: {user.name}): {e}", exc_info=True)
            db.rollback()

    async def trigger_push(self, user_id, trigger_reason: str = "manual"):
        """手动触发推送（供测试使用）"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                logger.info(f"[推送] 手动触发用户 {user.name} 的推送")
                await self._push_papers(db, user, trigger_reason=trigger_reason)
            else:
                logger.warning(f"[推送] 用户 {user_id} 不存在")
        finally:
            db.close()


# 全局调度器实例
scheduler = SchedulerService()
