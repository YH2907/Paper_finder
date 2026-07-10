"""测试论文推荐功能

测试 RecommendationService 的核心逻辑：
1. 在线搜索论文
2. 存入数据库
3. 返回推荐结果
4. 定时推送触发

使用方法：
    cd backend
    python -m scripts.test_recommendation
"""

import asyncio
import sys
import os

# 确保能导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, init_db
from app.models.user import User
from app.models.topic import Topic
from app.models.paper import Paper
from app.services.crawler.engine import CrawlerEngine
from app.services.recommendation_service import RecommendationService
from app.services.scheduler_service import SchedulerService


async def test_crawler_search():
    """测试爬虫搜索功能"""
    print("\n" + "=" * 60)
    print("测试 1: 爬虫搜索功能")
    print("=" * 60)

    crawler = CrawlerEngine()
    try:
        query = "large language model"
        print(f"搜索关键词: {query}")

        results = await crawler.search(query, limit=5)
        print(f"搜索结果数量: {len(results)}")

        for i, paper in enumerate(results[:3], 1):
            print(f"\n  论文 {i}:")
            print(f"    标题: {paper.get('title', 'N/A')[:80]}")
            print(f"    来源: {paper.get('source', 'N/A')}")
            print(f"    DOI: {paper.get('doi', 'N/A')}")
            print(f"    发布日期: {paper.get('published', 'N/A')}")

        return len(results) > 0
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        return False
    finally:
        await crawler.close()


async def test_recommendation_service():
    """测试推荐服务"""
    print("\n" + "=" * 60)
    print("测试 2: 推荐服务")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 查找一个有主题的用户
        user = db.query(User).first()
        if not user:
            print("❌ 数据库中没有用户，跳过测试")
            return False

        print(f"测试用户: {user.name} ({user.id})")

        # 检查用户主题
        topics = db.query(Topic).filter(Topic.user_id == user.id, Topic.is_active == True).all()
        print(f"活跃主题数量: {len(topics)}")

        for topic in topics:
            print(f"  主题: {topic.name}")
            print(f"    关键词: {topic.keywords}")
            print(f"    排除词: {topic.exclude_keywords}")

        if not topics:
            print("⚠️ 用户没有活跃主题，将测试无主题推荐")

        # 测试推荐
        crawler = CrawlerEngine()
        try:
            rec_service = RecommendationService(db=db, crawler_engine=crawler)

            print("\n开始获取推荐...")
            papers = await rec_service.fetch_and_recommend(
                user_id=user.id,
                limit=5,
                force_online=True,
                only_unseen=False,
            )

            print(f"推荐结果数量: {len(papers)}")

            for i, paper in enumerate(papers[:3], 1):
                print(f"\n  推荐论文 {i}:")
                print(f"    标题: {paper.title[:80]}")
                print(f"    来源: {paper.source}")
                print(f"    发布日期: {paper.published_at}")

            return len(papers) > 0
        finally:
            await crawler.close()

    except Exception as e:
        print(f"❌ 推荐测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_scheduler_trigger():
    """测试定时推送触发"""
    print("\n" + "=" * 60)
    print("测试 3: 定时推送触发")
    print("=" * 60)

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("❌ 数据库中没有用户，跳过测试")
            return False

        print(f"测试用户: {user.name}")
        print(f"推送配置: enabled={user.push_enabled}, frequency={user.push_frequency}, time={user.push_time}")

        scheduler = SchedulerService()
        print("\n手动触发推送...")
        await scheduler.trigger_push(user.id, trigger_reason="test")

        # 检查通知
        from app.models.notification import Notification
        notifications = (
            db.query(Notification)
            .filter(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(5)
            .all()
        )

        print(f"用户通知数量: {len(notifications)}")
        for n in notifications[:3]:
            print(f"  通知: {n.title}")
            print(f"    内容: {n.content[:100]}...")

        return True

    except Exception as e:
        print(f"❌ 推送测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_database_persistence():
    """测试数据持久化"""
    print("\n" + "=" * 60)
    print("测试 4: 数据持久化")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 统计论文数量
        paper_count = db.query(Paper).count()
        print(f"数据库中论文总数: {paper_count}")

        # 检查最近的论文
        recent_papers = (
            db.query(Paper)
            .order_by(Paper.created_at.desc())
            .limit(5)
            .all()
        )

        print(f"最近 5 篇论文:")
        for p in recent_papers:
            print(f"  - {p.title[:60]}")
            print(f"    来源: {p.source}, 创建时间: {p.created_at}")

        return True

    except Exception as e:
        print(f"❌ 持久化测试失败: {e}")
        return False
    finally:
        db.close()


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("论文推荐功能测试")
    print("=" * 60)

    # 初始化数据库
    init_db()

    results = {}

    # 测试 1: 爬虫搜索
    results["爬虫搜索"] = await test_crawler_search()

    # 测试 2: 推荐服务
    results["推荐服务"] = await test_recommendation_service()

    # 测试 3: 定时推送
    results["定时推送"] = await test_scheduler_trigger()

    # 测试 4: 数据持久化
    results["数据持久化"] = await test_database_persistence()

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败，请检查日志")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
