"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Search,
  Plus,
  MessageSquare,
  Settings,
  FileText,
  FolderOpen,
  Clock,
  ArrowRight,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface SearchResult {
  type: "paper" | "topic";
  title: string;
  description: string;
  icon: React.ReactNode;
}

const recentSearches = [
  "Transformer attention mechanism",
  "大语言模型微调方法",
  "RAG 检索增强生成",
];

const sampleResults: SearchResult[] = [
  {
    type: "paper",
    title: "Attention Is All You Need",
    description: "Vaswani et al. · NeurIPS 2017",
    icon: <FileText className="size-4 text-blue-500" />,
  },
  {
    type: "paper",
    title: "BERT: Pre-training of Deep Bidirectional Transformers",
    description: "Devlin et al. · NAACL 2019",
    icon: <FileText className="size-4 text-blue-500" />,
  },
  {
    type: "topic",
    title: "自然语言处理",
    description: "12 篇论文 · 3 个关键词",
    icon: <FolderOpen className="size-4 text-green-500" />,
  },
  {
    type: "topic",
    title: "大语言模型",
    description: "8 篇论文 · 5 个关键词",
    icon: <FolderOpen className="size-4 text-green-500" />,
  },
];

const quickActions = [
  { label: "添加研究主题", icon: <Plus className="size-4" />, shortcut: "N" },
  {
    label: "新建对话",
    icon: <MessageSquare className="size-4" />,
    shortcut: "C",
  },
  { label: "打开设置", icon: <Settings className="size-4" />, shortcut: "," },
];

export function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);

  // 全局快捷键 Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // 模拟搜索
  const handleSearch = useCallback((value: string) => {
    setQuery(value);
    if (value.trim()) {
      setResults(
        sampleResults.filter(
          (r) =>
            r.title.toLowerCase().includes(value.toLowerCase()) ||
            r.description.toLowerCase().includes(value.toLowerCase())
        )
      );
    } else {
      setResults([]);
    }
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent
        className="sm:max-w-lg max-h-[80vh] overflow-hidden flex flex-col"
        showCloseButton={false}
      >
        {/* 搜索输入 */}
        <div className="flex items-center gap-2 px-1">
          <Search className="size-4 text-muted-foreground shrink-0" />
          <input
            type="text"
            placeholder="搜索论文、主题、对话..."
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            autoFocus
          />
          <kbd className="pointer-events-none h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
            ESC
          </kbd>
        </div>

        <Separator />

        {/* 搜索结果 / 默认内容 */}
        <div className="flex-1 overflow-y-auto -mx-1">
          {query && results.length > 0 ? (
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground px-1 py-1">
                搜索结果
              </p>
              {results.map((result, i) => (
                <button
                  key={i}
                  className="flex items-center gap-3 w-full px-2 py-2 rounded-lg hover:bg-muted text-left transition-colors"
                >
                  {result.icon}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {result.title}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {result.description}
                    </p>
                  </div>
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-[10px] shrink-0",
                      result.type === "paper"
                        ? "border-blue-200 text-blue-600"
                        : "border-green-200 text-green-600"
                    )}
                  >
                    {result.type === "paper" ? "论文" : "主题"}
                  </Badge>
                </button>
              ))}
            </div>
          ) : query && results.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Search className="size-8 mb-2 opacity-40" />
              <p className="text-sm">未找到匹配的结果</p>
            </div>
          ) : (
            <div className="space-y-3">
              {/* 最近搜索 */}
              {recentSearches.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground px-1 py-1 flex items-center gap-1">
                    <Clock className="size-3" />
                    最近搜索
                  </p>
                  <div className="space-y-0.5">
                    {recentSearches.map((term, i) => (
                      <button
                        key={i}
                        onClick={() => handleSearch(term)}
                        className="flex items-center gap-3 w-full px-2 py-1.5 rounded-lg hover:bg-muted text-left transition-colors"
                      >
                        <Clock className="size-3.5 text-muted-foreground/50" />
                        <span className="text-sm text-muted-foreground">
                          {term}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <Separator />

              {/* 快捷操作 */}
              <div>
                <p className="text-xs font-medium text-muted-foreground px-1 py-1">
                  快捷操作
                </p>
                <div className="space-y-0.5">
                  {quickActions.map((action, i) => (
                    <button
                      key={i}
                      className="flex items-center gap-3 w-full px-2 py-1.5 rounded-lg hover:bg-muted text-left transition-colors"
                    >
                      <span className="text-muted-foreground">
                        {action.icon}
                      </span>
                      <span className="text-sm flex-1">{action.label}</span>
                      <kbd className="pointer-events-none h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                        {action.shortcut}
                      </kbd>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 底部提示 */}
        <Separator />
        <div className="flex items-center justify-between text-[10px] text-muted-foreground px-1">
          <span>↑↓ 导航 · ↵ 选择 · ESC 关闭</span>
          <span className="flex items-center gap-1">
            <kbd className="rounded border bg-muted px-1 font-mono">⌘</kbd>
            <kbd className="rounded border bg-muted px-1 font-mono">K</kbd>
            搜索
          </span>
        </div>
      </DialogContent>
    </Dialog>
  );
}
