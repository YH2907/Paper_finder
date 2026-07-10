# Paper Finder Agent - 设计系统

> **主题**: 亮色模式 | **风格**: 简洁学术 | **语言**: 中文

---

## 1. 色彩系统

### 1.1 主色 (Primary)

用于主要操作按钮、链接、选中状态。

| Token | 色值 | 用途 |
|-------|------|------|
| `primary` | #2563eb | **主色** |
| `primary-hover` | #1d4ed8 | 按钮 hover |
| `primary-light` | #dbeafe | 浅色背景 |

### 1.2 辅色 (Secondary)

用于 AI 相关功能。

| Token | 色值 | 用途 |
|-------|------|------|
| `secondary` | #f1f5f9 | 次要背景 |
| `secondary-foreground` | #0f172a | 次要文字 |

### 1.3 语义色

| 语义 | 色值 | 用途 |
|------|------|------|
| Success | #22c55e | 成功、收藏 |
| Warning | #f59e0b | 警告、待处理 |
| Error | #ef4444 | 错误、删除 |
| Info | #0ea5e9 | 信息、提示 |

### 1.4 中性色

| Token | 色值 | 用途 |
|-------|------|------|
| `background` | #ffffff | 页面背景 |
| `foreground` | #0f172a | 主文字 |
| `muted` | #f1f5f9 | 次要背景 |
| `muted-foreground` | #64748b | 次要文字 |
| `border` | #e2e8f0 | 边框 |

---

## 2. 字体系统

### 2.1 字体族

```css
--font-sans: 'Geist Sans', -apple-system, 'PingFang SC', sans-serif;
--font-mono: 'Geist Mono', 'JetBrains Mono', monospace;
```

### 2.2 字号

| Token | 大小 | 用途 |
|-------|------|------|
| `text-xs` | 12px | 标签、辅助信息 |
| `text-sm` | 14px | 次要文字 |
| `text-base` | 16px | **正文默认** |
| `text-lg` | 18px | 卡片标题 |
| `text-xl` | 20px | 页面小标题 |
| `text-2xl` | 24px | 页面标题 |
| `text-3xl` | 30px | 大标题 |

---

## 3. 间距系统

基于 4px 网格。

| Token | 大小 | 用途 |
|-------|------|------|
| `1` | 4px | 紧凑间距 |
| `2` | 8px | 小间距 |
| `3` | 12px | 元素内间距 |
| `4` | 16px | **默认间距** |
| `6` | 24px | 卡片内间距 |
| `8` | 32px | 大间距 |

---

## 4. 圆角系统

| Token | 大小 | 用途 |
|-------|------|------|
| `rounded-sm` | 4px | 标签 |
| `rounded-md` | 6px | 按钮、输入框 |
| `rounded-lg` | 8px | 卡片 |
| `rounded-xl` | 12px | 弹窗 |
| `rounded-full` | 9999px | 圆形 |

---

## 5. 阴影系统

| Token | 用途 |
|-------|------|
| `shadow-sm` | 标签、小元素 |
| `shadow` | 卡片、输入框 |
| `shadow-md` | 悬浮状态 |
| `shadow-lg` | 弹窗、模态框 |

---

## 6. 按钮系统

### 6.1 变体

| 变体 | 样式 | 用途 |
|------|------|------|
| Primary | 蓝色背景、白色文字 | 主要操作 |
| Secondary | 白色背景、边框 | 次要操作 |
| Ghost | 透明背景 | 图标按钮 |
| Danger | 红色背景 | 删除操作 |
| Link | 无背景、下划线 | 文字链接 |

### 6.2 尺寸

| 尺寸 | 高度 | 用途 |
|------|------|------|
| sm | 32px | 紧凑按钮 |
| md | 40px | **默认** |
| lg | 48px | 大按钮 |
| icon | 40px | 图标按钮 |

---

## 7. 卡片系统

### 7.1 论文卡片

```
┌─────────────────────────────────────────────────────────┐
│  📄 论文标题                              [✓ 已读]      │
│  👤 作者                                             │
│  🏷️ 来源 · 📅 日期                                    │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 💡 AI 摘要                                        │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  [🔗 原文] [⭐ 收藏] [💬 提问] [📖 已读]               │
└─────────────────────────────────────────────────────────┘
```

- 背景: `bg-white`
- 边框: `border border-neutral-200`
- 圆角: `rounded-lg`
- 阴影: `shadow-sm` → hover `shadow-md`
- AI区域: `bg-purple-50`

---

## 8. 输入框系统

| 状态 | 样式 |
|------|------|
| Default | 白色背景、灰色边框 |
| Focus | 蓝色边框、蓝色光晕 |
| Error | 红色边框、红色光晕 |
| Disabled | 灰色背景、禁用光标 |

---

## 9. 动画系统

| 场景 | 动画 | 时间 |
|------|------|------|
| 按钮点击 | scale(0.98) | 75ms |
| 卡片悬浮 | 阴影变化 | 200ms |
| 收藏点击 | 弹跳 | 300ms |
| 弹窗打开 | 缩放淡入 | 200ms |
| Toast | 从右滑入 | 300ms |

---

## 10. 布局系统

| 元素 | 尺寸 |
|------|------|
| Sidebar | w-56 (224px) |
| 内容区 | max-w-5xl (1024px) |
| 页面内边距 | p-6 (24px) |
| 卡片间距 | gap-4 (16px) |

---

## 11. CSS 变量

```css
:root {
  --background: #ffffff;
  --foreground: #0f172a;
  --primary: #2563eb;
  --primary-foreground: #ffffff;
  --secondary: #f1f5f9;
  --muted: #f1f5f9;
  --muted-foreground: #64748b;
  --border: #e2e8f0;
  --destructive: #ef4444;
  --radius: 0.5rem;
}
```
