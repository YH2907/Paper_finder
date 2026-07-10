# Paper Finder Backend

> 后端 API 服务

---

## 技术栈

- FastAPI
- SQLAlchemy 2.0
- PostgreSQL + pgvector
- Redis
- Celery

---

## 快速开始

### 1. 创建虚拟环境

```bash
cd ~/paper-finder-agent/backend
python -m venv venv
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库和 AI API Key
```

### 4. 启动数据库

```bash
docker-compose up -d postgres redis
```

### 5. 运行数据库迁移

```bash
alembic upgrade head
```

### 6. 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档

---

## 项目结构

```
backend/
├── app/
│   ├── api/            # API 路由
│   │   └── v1/         # v1 版本
│   ├── core/           # 核心模块
│   │   ├── security.py # JWT 认证
│   │   ├── database.py # 数据库连接
│   │   ├── redis.py    # Redis 连接
│   │   └── celery_app.py
│   ├── models/         # SQLAlchemy 模型
│   ├── schemas/        # Pydantic Schema
│   ├── services/       # 业务服务
│   │   ├── crawler/    # 论文爬虫
│   │   ├── ai/         # AI 服务
│   │   └── notification/
│   └── utils/          # 工具函数
├── alembic/            # 数据库迁移
├── tests/              # 测试
├── requirements.txt
└── Dockerfile
```

---

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 主要端点

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | POST /api/v1/auth/register | 注册 |
| 认证 | POST /api/v1/auth/login | 登录 |
| 主题 | GET /api/v1/topics | 获取主题列表 |
| 主题 | POST /api/v1/topics | 创建主题 |
| 论文 | GET /api/v1/papers | 获取论文列表 |
| 论文 | GET /api/v1/papers/{id} | 获取论文详情 |
| 对话 | GET /api/v1/chat | 获取对话列表 |
| 对话 | POST /api/v1/chat/{id}/messages | 发送消息 |

---

## 数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

---

## 测试

```bash
pytest tests/ -v
```
