"""数据库初始化脚本

创建表和示例数据
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import engine, SessionLocal, Base
from app.models import user, topic, paper, chat, message, user_paper  # noqa
from app.core.security import get_password_hash


def init_database():
    """初始化数据库"""
    print("🔧 创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建完成")


def create_sample_data():
    """创建示例数据"""
    db = SessionLocal()
    try:
        # 检查是否已有数据
        from app.models.user import User
        existing_user = db.query(User).first()
        if existing_user:
            print("ℹ️ 数据库已有数据，跳过示例数据创建")
            return
        
        print("📝 创建示例数据...")
        
        # 创建用户
        from app.models.user import User
        user = User(
            email="demo@example.com",
            name="演示用户",
            password_hash=get_password_hash("Demo123"),  # 密码不超过72字节
        )
        db.add(user)
        db.flush()
        
        # 创建主题
        from app.models.topic import Topic
        topics = [
            Topic(
                user_id=user.id,
                name="大语言模型",
                keywords=["LLM", "大语言模型", "GPT", "Transformer"],
                exclude_keywords=["综述", "survey"],
                is_active=True,
            ),
            Topic(
                user_id=user.id,
                name="多模态学习",
                keywords=["multimodal", "多模态", "vision language", "CLIP"],
                exclude_keywords=[],
                is_active=True,
            ),
        ]
        db.add_all(topics)
        db.flush()
        
        # 创建示例论文
        from app.models.paper import Paper
        papers = [
            Paper(
                title="Attention Is All You Need",
                authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
                abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
                url="https://arxiv.org/abs/1706.03762",
                doi="10.48550/arXiv.1706.03762",
                source="arxiv",
                ai_summary="提出了 Transformer 架构，完全基于注意力机制，摒弃了传统的 RNN 和 CNN 结构。",
                ai_problem_solved="解决了 RNN 长序列依赖问题，实现了真正的并行计算。",
            ),
            Paper(
                title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
                authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee"],
                abstract="We introduce a new language representation model called BERT...",
                url="https://arxiv.org/abs/1810.04805",
                doi="10.48550/arXiv.1810.04805",
                source="arxiv",
                ai_summary="提出双向 Transformer 预训练模型 BERT，通过 MLM 和 NSP 两个预训练任务。",
                ai_problem_solved="解决了单向语言模型无法充分利用上下文信息的问题。",
            ),
            Paper(
                title="GPT-4 Technical Report",
                authors=["OpenAI"],
                abstract="We report the development of GPT-4, a large-scale, multimodal model...",
                url="https://arxiv.org/abs/2303.08774",
                doi="10.48550/arXiv.2303.08774",
                source="arxiv",
                ai_summary="OpenAI 发布的 GPT-4 技术报告，展示了大规模多模态模型的卓越表现。",
                ai_problem_solved="推动了 AI 在各种专业和学术基准上的应用。",
            ),
        ]
        db.add_all(papers)
        db.flush()
        
        # 创建用户论文关联
        from app.models.user_paper import UserPaper
        user_papers = [
            UserPaper(
                user_id=user.id,
                paper_id=papers[0].id,
                is_read=True,
                is_bookmarked=True,
            ),
            UserPaper(
                user_id=user.id,
                paper_id=papers[1].id,
                is_read=False,
                is_bookmarked=False,
            ),
        ]
        db.add_all(user_papers)
        
        # 创建示例对话
        from app.models.chat import Chat
        from app.models.message import Message
        chat = Chat(
            user_id=user.id,
            title="关于 Transformer 的讨论",
        )
        db.add(chat)
        db.flush()
        
        messages = [
            Message(chat_id=chat.id, role="user", content="Transformer 的核心思想是什么？"),
            Message(chat_id=chat.id, role="assistant", content="Transformer 的核心思想是完全基于注意力机制，摒弃了传统的 RNN 和 CNN 结构。它通过自注意力机制直接建模序列中任意两个位置之间的依赖关系，实现了真正的并行计算。"),
        ]
        db.add_all(messages)
        
        db.commit()
        print("✅ 示例数据创建完成")
        print(f"   - 用户: demo@example.com / Demo123")
        print(f"   - 主题: {len(topics)} 个")
        print(f"   - 论文: {len(papers)} 篇")
        print(f"   - 对话: 1 个")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 创建示例数据失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
    create_sample_data()
