"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ExternalLink,
  Bookmark,
  BookmarkCheck,
  MessageCircle,
  Send,
  Sparkles,
  FileText,
  Calendar,
  User,
  Globe,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  getPaper,
  bookmarkPaper,
  unbookmarkPaper,
  markPaperRead,
  createChat,
  sendMessage,
  type Paper,
  type Message,
} from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export default function PaperDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();

  const [paper, setPaper] = useState<Paper | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [bookmarkLoading, setBookmarkLoading] = useState(false);

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);
  const [chatId, setChatId] = useState<string | null>(null);

  useEffect(() => {
    async function loadPaper() {
      setLoading(true);
      setError("");
      try {
        const res = await getPaper(id);
        if (res.success) {
          setPaper(res.data);
          setIsBookmarked(res.data.is_bookmarked);
          // Mark as read (only if not already read)
          if (!res.data.is_read) {
            markPaperRead(id).catch(() => {});
          }
        } else {
          setError("加载论文失败");
        }
      } catch {
        setError("加载论文失败，请稍后重试");
      } finally {
        setLoading(false);
      }
    }
    loadPaper();
  }, [id]);

  const handleBookmark = async () => {
    if (!paper || bookmarkLoading) return;
    setBookmarkLoading(true);
    try {
      if (isBookmarked) {
        await unbookmarkPaper(paper.id);
        setIsBookmarked(false);
      } else {
        await bookmarkPaper(paper.id);
        setIsBookmarked(true);
      }
    } catch {
      // ignore
    } finally {
      setBookmarkLoading(false);
    }
  };

  const handleStartChat = async () => {
    if (!paper) return;
    try {
      const res = await createChat(`关于「${paper.title}」的对话`, paper.id);
      if (res.success) {
        setChatId(res.data.id);
        setMessages([
          {
            role: "assistant",
            content: `您好！我已阅读了「${paper.title}」这篇论文。您可以向我提问关于论文的任何问题，比如核心方法、实验结果、与现有工作的对比等。`,
          },
        ]);
      }
    } catch {
      // ignore
    }
  };

  const handleSend = async () => {
    if (!inputValue.trim() || sending) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setSending(true);

    try {
      // If no chat yet, create one first
      let currentChatId = chatId;
      if (!currentChatId && paper) {
        const chatRes = await createChat(
          `关于「${paper.title}」的对话`,
          paper.id
        );
        if (chatRes.success) {
          currentChatId = chatRes.data.id;
          setChatId(currentChatId);
        }
      }

      if (currentChatId) {
        const res = await sendMessage(currentChatId, userMessage);
        if (res.success) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: res.data.content },
          ]);
        }
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "抱歉，发送消息失败，请稍后重试。",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !paper) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-4">
        <p className="text-red-500">{error || "论文不存在"}</p>
        <Link href="/papers">
          <Button variant="outline">返回论文列表</Button>
        </Link>
      </div>
    );
  }

  const authorsStr = paper.authors?.join(", ") || "未知作者";
  const dateStr = paper.published_at
    ? new Date(paper.published_at).toLocaleDateString("zh-CN")
    : "未知日期";

  return (
    <div className="flex flex-col h-full">
      {/* 顶部导航 */}
      <div className="flex items-center gap-3 border-b px-6 py-3">
        <Link href="/papers">
          <Button variant="ghost" size="icon-sm">
            <ArrowLeft className="size-4" />
          </Button>
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-base font-semibold truncate">{paper.title}</h1>
          <p className="text-xs text-muted-foreground truncate">
            {authorsStr} · {paper.source || "未知来源"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {paper.url && (
            <a href={paper.url} target="_blank" rel="noopener noreferrer">
              <Button variant="outline" size="sm">
                <ExternalLink className="size-3.5" />
                访问原文
              </Button>
            </a>
          )}
          <Button
            variant={isBookmarked ? "default" : "outline"}
            size="sm"
            onClick={handleBookmark}
            disabled={bookmarkLoading}
          >
            {isBookmarked ? (
              <BookmarkCheck className="size-3.5" />
            ) : (
              <Bookmark className="size-3.5" />
            )}
            {isBookmarked ? "已收藏" : "收藏"}
          </Button>
          <Button variant="outline" size="sm" onClick={handleStartChat}>
            <MessageCircle className="size-3.5" />
            开始对话
          </Button>
        </div>
      </div>

      {/* 主内容区 */}
      <div className="flex flex-1 overflow-hidden">
        {/* 左侧：论文信息 */}
        <div className="w-1/2 overflow-y-auto p-6 space-y-4 border-r">
          {/* 基本信息 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{paper.title}</CardTitle>
              <CardDescription className="space-y-1.5 pt-1">
                <span className="flex items-center gap-1.5">
                  <User className="size-3.5" />
                  {authorsStr}
                </span>
                {paper.source && (
                  <span className="flex items-center gap-1.5">
                    <Globe className="size-3.5" />
                    {paper.source}
                  </span>
                )}
                {paper.published_at && (
                  <span className="flex items-center gap-1.5">
                    <Calendar className="size-3.5" />
                    {dateStr}
                  </span>
                )}
                {paper.doi && (
                  <span className="flex items-center gap-1.5 text-xs">
                    DOI: {paper.doi}
                  </span>
                )}
              </CardDescription>
            </CardHeader>
          </Card>

          {/* 原文摘要 */}
          {paper.abstract && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <FileText className="size-4" />
                  原文摘要
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {paper.abstract}
                </p>
              </CardContent>
            </Card>
          )}

          {/* AI 分析卡片 */}
          {(paper.ai_summary || paper.ai_problem_solved) && (
            <Card className="bg-purple-50 dark:bg-purple-950/20 ring-purple-200 dark:ring-purple-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm text-purple-700 dark:text-purple-300">
                  <Sparkles className="size-4" />
                  AI 智能分析
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {paper.ai_summary && (
                  <div>
                    <h4 className="text-xs font-semibold text-purple-600 dark:text-purple-400 mb-2">
                      核心贡献
                    </h4>
                    <p className="text-sm text-foreground/80 leading-relaxed">
                      {paper.ai_summary}
                    </p>
                  </div>
                )}

                {paper.ai_summary && paper.ai_problem_solved && (
                  <Separator className="bg-purple-200 dark:bg-purple-800" />
                )}

                {paper.ai_problem_solved && (
                  <div>
                    <h4 className="text-xs font-semibold text-purple-600 dark:text-purple-400 mb-2">
                      解决的问题
                    </h4>
                    <p className="text-sm text-foreground/80 leading-relaxed">
                      {paper.ai_problem_solved}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* 右侧：对话区域 */}
        <div className="flex flex-col w-1/2">
          <div className="flex items-center gap-2 border-b px-4 py-2.5">
            <MessageCircle className="size-4 text-muted-foreground" />
            <span className="text-sm font-medium">论文对话</span>
          </div>

          {/* 对话消息 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
                <MessageCircle className="size-10 mb-3 opacity-30" />
                <p className="text-sm">点击「开始对话」按钮开始与 AI 讨论这篇论文</p>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                >
                  <div
                    className={`size-7 rounded-full flex items-center justify-center shrink-0 ${
                      msg.role === "user"
                        ? "bg-primary/10"
                        : "bg-purple-100 dark:bg-purple-900/40"
                    }`}
                  >
                    {msg.role === "user" ? (
                      <User className="size-3.5 text-primary" />
                    ) : (
                      <Sparkles className="size-3.5 text-purple-600 dark:text-purple-400" />
                    )}
                  </div>
                  <div className={`flex-1 ${msg.role === "user" ? "text-right" : ""}`}>
                    <p className="text-xs font-medium text-muted-foreground mb-1">
                      {msg.role === "user" ? "您" : "AI 助手"}
                    </p>
                    <div
                      className={`rounded-lg p-3 text-sm leading-relaxed inline-block text-left ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      }`}
                    >
                      {msg.content.split("\n").map((line, j) => (
                        <span key={j}>
                          {line.startsWith("**") ? (
                            <strong>{line.replace(/\*\*/g, "")}</strong>
                          ) : (
                            line
                          )}
                          {j < msg.content.split("\n").length - 1 && <br />}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))
            )}
            {sending && (
              <div className="flex gap-3">
                <div className="size-7 rounded-full bg-purple-100 dark:bg-purple-900/40 flex items-center justify-center shrink-0">
                  <Sparkles className="size-3.5 text-purple-600 dark:text-purple-400" />
                </div>
                <div className="flex-1">
                  <p className="text-xs font-medium text-muted-foreground mb-1">
                    AI 助手
                  </p>
                  <div className="bg-muted rounded-lg p-3 text-sm">
                    <Loader2 className="size-4 animate-spin" />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 输入框 */}
          <div className="border-t p-3">
            <div className="flex gap-2">
              <Input
                placeholder="输入关于这篇论文的问题..."
                value={inputValue}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setInputValue(e.target.value)
                }
                onKeyDown={(e: React.KeyboardEvent) =>
                  e.key === "Enter" && !e.shiftKey && handleSend()
                }
                className="flex-1"
                disabled={sending}
              />
              <Button
                size="icon"
                onClick={handleSend}
                disabled={!inputValue.trim() || sending}
              >
                {sending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Send className="size-4" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
