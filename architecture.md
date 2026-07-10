# Paper Finder Agent - 系统架构设计文档

> **状态**: ✅ 已确认 | **成本**: 完全免费

---

## 1. 技术选型

| 组件 | 选型 | 费用 |
|------|------|------|
| 前端框架 | Next.js 16 + React 19 | 免费 |
| UI组件库 | shadcn/ui + Tailwind CSS v4 | 免费 |
| 后端框架 | FastAPI (Python) | 免费 |
| 数据库 | PostgreSQL + pgvector | 免费 |
| 缓存/队列 | Redis | 免费 |
| AI模型 | Groq (Llama3 70B) + Gemini (备用) | 免费 |
| 论文源 | arXiv + Semantic Scholar + OpenAlex | 免费 |
| 部署 | Docker Compose | 免费 |

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Next.js)                        │
│         http://localhost:3000                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   API 网关 (Traefik)                     │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  用户服务    │  │  论文服务    │  │  AI 服务     │
│  (FastAPI)   │  │  (FastAPI)   │  │  (FastAPI)   │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│            PostgreSQL + pgvector + Redis                 │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 前端架构

### 3.1 路由结构

```
src/app/
├── layout.tsx              # 根布局
├── page.tsx                # 主面板 (/)
├── globals.css             # 设计系统
│
├── (auth)/                 # 认证页面
│   ├── login/page.tsx      # 登录
│   └── register/page.tsx   # 注册
│
└── (dashboard)/            # 仪表盘布局
    ├── layout.tsx          # 侧边栏布局
    ├── papers/
    │   ├── page.tsx        # 论文列表
    │   └── [id]/page.tsx   # 论文详情
    ├── topics/page.tsx     # 主题管理
    ├── chat/page.tsx       # AI对话
    ├── bookmarks/page.tsx  # 收藏夹
    ├── notifications/page.tsx # 通知
    └── settings/page.tsx   # 设置
```

### 3.2 组件结构

```
src/components/
├── layout/
│   ├── Header.tsx
│   ├── Sidebar.tsx
│   └── MainLayout.tsx
├── papers/
│   └── PaperCard.tsx
├── search/
│   └── GlobalSearch.tsx
├── onboarding/
│   └── OnboardingFlow.tsx
├── export/
│   └── ExportDialog.tsx
├── common/
│   └── KeyboardHelp.tsx
└── ui/                     # shadcn/ui 组件
```

---

## 4. 后端架构

### 4.1 服务划分

| 服务 | 职责 |
|------|------|
| 用户服务 | 注册、登录、用户管理 |
| 论文服务 | 论文检索、存储、查询 |
| AI服务 | 论文分析、对话、摘要 |
| 推送服务 | 定时推送、通知 |

### 4.2 数据模型

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(100),
    password_hash VARCHAR(255),
    created_at TIMESTAMP
);

-- 研究主题表
CREATE TABLE topics (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(200),
    keywords TEXT[],
    exclude_keywords TEXT[],
    is_active BOOLEAN
);

-- 论文表
CREATE TABLE papers (
    id UUID PRIMARY KEY,
    title VARCHAR(500),
    authors TEXT[],
    abstract TEXT,
    url VARCHAR(500),
    doi VARCHAR(100),
    source VARCHAR(50),
    published_at TIMESTAMP,
    ai_summary TEXT,
    ai_problem_solved TEXT,
    embedding VECTOR(384)
);
```

---

## 5. AI 模型

### 5.1 降级策略

```
请求 → Groq (主力)
         ↓ 失败/限流
       Gemini (备用)
         ↓ 失败
       返回缓存结果
```

### 5.2 免费额度

| 平台 | 免费额度 | 模型 |
|------|----------|------|
| Groq | 30请求/分钟 | Llama3 70B |
| Gemini | 15请求/分钟 | Gemini 1.5 Flash |

---

## 6. 论文数据源

| 数据源 | 费用 | 限制 |
|--------|------|------|
| arXiv | 免费 | 3秒/请求 |
| Semantic Scholar | 免费 | 100请求/5分钟 |
| OpenAlex | 免费 | 10000请求/天 |

---

## 7. 部署架构

```
docker-compose.yml
├── frontend (Next.js)      # Port 3000
├── backend (FastAPI)       # Port 8000
├── postgres                # Port 5432
├── redis                   # Port 6379
└── traefik                 # Port 80, 443
```

---

## 8. 开发状态

| 阶段 | 状态 | 说明 |
|------|------|------|
| 前端页面 | ✅ 完成 | 10个页面已实现 |
| 后端API | 🚧 进行中 | 待开发 |
| 数据库 | 📋 待定 | 待设计 |
| AI集成 | 📋 待定 | 待接入 |
| 部署 | 📋 待定 | 待配置 |
