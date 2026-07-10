# Paper Finder Agent

> 自动发现学术论文 · AI 帮你读懂每篇

---

## 项目简介

Paper Finder Agent 是一个智能化的论文检索与推荐系统，能够根据用户设定的研究兴趣，自动从学术数据库中搜索、筛选并推送相关论文。

### 核心功能

- 🔍 **智能检索** - 连接 arXiv、Semantic Scholar、OpenAlex 等多个学术数据源
- 🤖 **AI 分析** - 自动生成论文摘要、分析能解决什么问题
- 💬 **AI 对话** - 就论文内容与 AI 进行对话
- 📬 **定时推送** - 按设定周期推送最新论文
- ⭐ **收藏管理** - 收藏和管理感兴趣的论文

### 技术栈

| 组件 | 技术 | 费用 |
|------|------|------|
| 前端 | Next.js + shadcn/ui | 免费 |
| 后端 | FastAPI + PostgreSQL | 免费 |
| AI | Groq + Gemini | 免费 |
| 论文源 | arXiv + Semantic Scholar | 免费 |

**总成本: $0**

---

## 快速开始

### 方式一：本地开发

```bash
# 1. 克隆项目
cd ~/paper-finder-agent

# 2. 启动数据库
docker-compose up -d postgres redis

# 3. 安装后端依赖
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. 启动后端
uvicorn app.main:app --reload --port 8000

# 5. 安装前端依赖
cd ../frontend
npm install

# 6. 启动前端
npm run dev
```

访问 http://localhost:3000

### 方式二：Docker Compose

```bash
# 一键启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

---

## 项目结构

```
paper-finder-agent/
├── PRD.md                  # 产品需求文档
├── architecture.md         # 系统架构文档
├── design-system.md        # 设计系统文档
├── ui-pages.md             # 页面规划文档
├── docker-compose.yml      # Docker 编排
├── Makefile                # 常用命令
│
├── frontend/               # 前端项目
│   ├── src/
│   │   ├── app/            # 10个页面
│   │   └── components/     # UI 组件
│   └── README.md
│
└── backend/                # 后端项目
    ├── app/
    │   ├── api/            # API 路由
    │   ├── core/           # 核心模块
    │   ├── models/         # 数据模型
    │   ├── schemas/        # Pydantic Schema
    │   └── services/       # 业务服务
    ├── requirements.txt
    └── Dockerfile
```

---

## 文档

| 文档 | 说明 |
|------|------|
| [PRD.md](PRD.md) | 产品需求文档 |
| [architecture.md](architecture.md) | 系统架构文档 |
| [design-system.md](design-system.md) | 设计系统文档 |
| [ui-pages.md](ui-pages.md) | 页面规划文档 |
| [frontend/README.md](frontend/README.md) | 前端项目说明 |

---

## 开发状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 前端页面 | ✅ 完成 | 10个页面已实现 |
| 后端API | 🚧 开发中 | 待完成 |
| 数据库 | 📋 待定 | 待配置 |
| AI集成 | 📋 待定 | 待接入 |
| 部署 | 📋 待定 | 待配置 |

---

## 常用命令

```bash
# 查看所有命令
make help

# 启动开发
make dev

# Docker 操作
make docker-up
make docker-down

# 数据库迁移
make db-migrate msg="添加用户表"
make db-upgrade

# 代码检查
make lint
make format
```

---

## 环境变量

复制 `.env.example` 到 `.env` 并配置：

```bash
cp backend/.env.example backend/.env
```

主要配置：
- `DATABASE_URL` - PostgreSQL 连接
- `REDIS_URL` - Redis 连接
- `GROQ_API_KEY` - Groq AI API Key (免费)
- `GEMINI_API_KEY` - Gemini AI API Key (免费)

---

## 许可证

MIT License
