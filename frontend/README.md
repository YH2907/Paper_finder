# Paper Finder Agent - 前端项目

> **状态**: ✅ 已完成 | **框架**: Next.js 16 + shadcn/ui

---

## 快速启动

```bash
cd ~/paper-finder-agent/frontend
npm run dev
```

访问 http://localhost:3000

---

## 页面清单

| 页面 | 路由 | 说明 |
|------|------|------|
| 主面板 | `/` | 统计、最新推荐论文 |
| 论文列表 | `/papers` | 浏览、筛选论文 |
| 论文详情 | `/papers/[id]` | 详情、AI分析、对话 |
| 主题管理 | `/topics` | 管理研究主题 |
| AI对话 | `/chat` | 与AI对话 |
| 收藏夹 | `/bookmarks` | 收藏的论文 |
| 通知中心 | `/notifications` | 系统通知 |
| 设置 | `/settings` | 个人设置 |
| 登录 | `/login` | 用户登录 |
| 注册 | `/register` | 用户注册 |

---

## 功能组件

| 组件 | 功能 |
|------|------|
| GlobalSearch | 全局搜索 (⌘K) |
| OnboardingFlow | 3步新手引导 |
| ExportDialog | 导出弹窗 |
| KeyboardHelp | 快捷键帮助 |

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| ⌘K | 搜索论文 |
| ⌘N | 新建对话 |
| ⌘B | 收藏 |
| ⌘E | 导出 |
| ⌘/ | 快捷键帮助 |

---

## 技术栈

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS v4
- shadcn/ui
- Lucide Icons

---

## 设计系统

- 主色: #2563eb (Primary Blue)
- 亮色模式
- 中文界面
- 桌面端布局
