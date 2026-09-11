"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import {
  Send,
  Plus,
  MessageSquare,
  Bot,
  User,
  Sparkles,
  Trash2,
  Loader2,
  Zap,
  Search,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from "lucide-react";
import {
  getChats,
  getChat,
  getPaper,
  createChat,
  sendMessageStream,
  deleteChat,
  type ChatListItem,
  type Chat,
  type Message,
} from "@/lib/api";
import ChatMessageContent from "@/components/chat/ChatMessageContent";
import { useResearchState, type ResearchStage } from "@/contexts/ResearchContext";

/** 阶段显示名称映射 */
const stageLabels: Record<ResearchStage, string> = {
  idle: "",
  analyzing: "分析问题...",
  searching: "搜索论文...",
  ranking: "排序结果...",
  completing: "生成报告...",
  completed: "研究完成",
  error: "发生错误",
};

export default function ChatPage() {
  const {
    isStreaming,
    setIsStreaming,
    currentStage,
    setCurrentStage,
    progress,
    setProgress,
    streamingContent: researchStreamingContent,
    setStreamingContent: setResearchStreamingContent,
    currentQuery,
    setCurrentQuery,
    error: researchError,
    setError: setResearchError,
  } = useResearchState();

  const [conversations, setConversations] = useState<ChatListItem[]>([]);
  const [activeChat, setActiveChat] = useState<Chat | null>(null);
  const [activeId, setActiveId] = useState<string>("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [creating, setCreating] = useState(false);

  const [streamingContent, setStreamingContent] = useState("");
  const [showProgress, setShowProgress] = useState(true);
  const [linkedPaperUrl, setLinkedPaperUrl] = useState("");
  const [linkedPaperTitle, setLinkedPaperTitle] = useState("");
  const [loadingLinkedPaper, setLoadingLinkedPaper] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamingContentRef = useRef("");

  const highlightKeywords = (currentQuery || "")
    .split(/[，,;；、\s]+/)
    .map((kw) => kw.trim())
    .filter((kw) => kw.length > 0);

  // 加载对话列表
  useEffect(() => {
    loadChats();
  }, []);

  // 滚动到底部
  useEffect(() => {
    scrollToBottom();
  }, [activeChat?.messages.length, streamingContent, researchStreamingContent]);

  // 组件卸载时取消流式请求
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // 加载当前对话关联论文的外链
  useEffect(() => {
    let cancelled = false;

    async function loadLinkedPaper() {
      if (!activeChat?.paper_id) {
        setLinkedPaperUrl("");
        setLinkedPaperTitle("");
        return;
      }

      setLoadingLinkedPaper(true);
      try {
        const res = await getPaper(activeChat.paper_id);
        if (!cancelled && res.success) {
          setLinkedPaperUrl(res.data.url || "");
          setLinkedPaperTitle(res.data.title || "");
        }
      } catch {
        if (!cancelled) {
          setLinkedPaperUrl("");
          setLinkedPaperTitle("");
        }
      } finally {
        if (!cancelled) {
          setLoadingLinkedPaper(false);
        }
      }
    }

    loadLinkedPaper();
    return () => {
      cancelled = true;
    };
  }, [activeChat?.paper_id]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  };

  async function loadChats() {
    try {
      const res = await getChats();
      if (res.success) {
        setConversations(res.data);
        // 自动选择第一个对话
        if (res.data.length > 0 && !activeId) {
          selectChat(res.data[0].id);
        }
      }
    } catch {
      // 忽略错误
    } finally {
      setLoading(false);
    }
  }

  async function selectChat(chatId: string) {
    setActiveId(chatId);
    try {
      const res = await getChat(chatId);
      if (res.success) {
        setActiveChat(res.data);
      }
    } catch {
      // 忽略错误
    }
  }

  /** 根据流式内容更新研究阶段 */
  const updateStageFromContent = useCallback(
    (content: string) => {
      if (content.includes("分析") || content.includes("理解")) {
        setCurrentStage("analyzing");
        setProgress(Math.min(progress + 5, 20));
      } else if (content.includes("搜索") || content.includes("查找")) {
        setCurrentStage("searching");
        setProgress(Math.min(progress + 3, 50));
      } else if (content.includes("排序") || content.includes("评估")) {
        setCurrentStage("ranking");
        setProgress(Math.min(progress + 5, 75));
      } else if (content.includes("总结") || content.includes("报告")) {
        setCurrentStage("completing");
        setProgress(Math.min(progress + 5, 95));
      }
    },
    [setCurrentStage, setProgress, progress]
  );

  const handleSend = useCallback(async () => {
    if (!input.trim() || sending) return;

    // 如果有正在进行的流式请求，先取消
    abortRef.current?.abort();

    let chatId = activeId;

    // 如果没有活跃对话，先自动创建一个
    if (!chatId) {
      setCreating(true);
      try {
        const createRes = await createChat(input.trim().slice(0, 20) || "新对话");
        if (!createRes.success) return;
        chatId = createRes.data.id;
        setConversations((prev) => [
          {
            id: createRes.data.id,
            title: createRes.data.title,
            paper_id: createRes.data.paper_id,
            created_at: createRes.data.created_at,
            last_message: null,
          },
          ...prev,
        ]);
        setActiveId(chatId);
      } catch {
        return;
      } finally {
        setCreating(false);
      }
    }

    const content = input;
    setInput("");
    setSending(true);
    setStreamingContent("");
    streamingContentRef.current = "";

    // 重置研究状态
    setCurrentStage("analyzing");
    setProgress(5);
    setCurrentQuery(content);
    setIsStreaming(true);

    // 先添加用户消息到界面
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    setActiveChat((prev) =>
      prev
        ? { ...prev, messages: [...prev.messages, tempUserMsg] }
        : {
            id: chatId!,
            title: "新对话",
            paper_id: null,
            created_at: new Date().toISOString(),
            messages: [tempUserMsg],
          }
    );

    // 使用流式 API
    const controller = sendMessageStream(
      chatId!,
      content,
      // onToken - 收到文本片段
      (token) => {
        streamingContentRef.current += token;
        setStreamingContent(streamingContentRef.current);
        // 根据内容更新阶段
        updateStageFromContent(token);
        scrollToBottom();
      },
      // onDone - 流结束
      async (messageId) => {
        // 用完整的流式内容创建 assistant 消息
        const finalContent = streamingContentRef.current;
        const assistantMsg: Message = {
          id: messageId || `stream-${Date.now()}`,
          role: "assistant",
          content: finalContent,
          created_at: new Date().toISOString(),
        };

        setActiveChat((prev) =>
          prev ? { ...prev, messages: [...prev.messages, assistantMsg] } : prev
        );
        setStreamingContent("");
        streamingContentRef.current = "";
        setSending(false);
        abortRef.current = null;

        // 标记完成
        setCurrentStage("completed");
        setProgress(100);
        setIsStreaming(false);

        // 刷新对话列表以获取更新的标题
        try {
          const chatRes = await getChat(chatId!);
          if (chatRes.success) {
            setActiveChat(chatRes.data);
            setConversations((prev) =>
              prev.map((c) =>
                c.id === chatId ? { ...c, title: chatRes.data.title } : c
              )
            );
          }
        } catch {
          // 忽略错误
        }
      },
      // onError - 出错
      (error) => {
        console.error("流式请求失败:", error);
        setStreamingContent("");
        streamingContentRef.current = "";
        setSending(false);
        abortRef.current = null;

        // 更新错误状态
        setCurrentStage("error");
        setProgress(0);
        setIsStreaming(false);
        setResearchError(error);

        // 如果没有流式内容，移除临时用户消息
        if (!streamingContentRef.current) {
          setActiveChat((prev) =>
            prev
              ? {
                  ...prev,
                  messages: prev.messages.filter(
                    (m) => m.id !== tempUserMsg.id
                  ),
                }
              : prev
          );
        }
      }
    );

    abortRef.current = controller;
  }, [
    input,
    sending,
    activeId,
    setCurrentStage,
    setProgress,
    setCurrentQuery,
    setIsStreaming,
    setResearchError,
    updateStageFromContent,
  ]);

  const handleNewConversation = async () => {
    if (creating) return;
    setCreating(true);
    try {
      const res = await createChat("新对话");
      if (res.success) {
        setConversations((prev) => [
          {
            id: res.data.id,
            title: res.data.title,
            paper_id: res.data.paper_id,
            created_at: res.data.created_at,
            last_message: null,
          },
          ...prev,
        ]);
        selectChat(res.data.id);
      }
    } catch {
      // 忽略错误
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteChat = async (chatId: string) => {
    if (!confirm("确定要删除这个对话吗？")) return;
    try {
      await deleteChat(chatId);
      setConversations((prev) => prev.filter((c) => c.id !== chatId));
      if (activeId === chatId) {
        setActiveChat(null);
        setActiveId("");
      }
    } catch {
      // 忽略错误
    }
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "刚刚";
    if (diffMins < 60) return `${diffMins} 分钟前`;
    if (diffHours < 24) return `${diffHours} 小时前`;
    if (diffDays < 7) return `${diffDays} 天前`;
    return date.toLocaleDateString("zh-CN");
  };



  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 overflow-hidden">
      {/* 左侧 - 对话列表 */}
      <div className="flex w-72 min-h-0 shrink-0 flex-col border-r border-border bg-card">
        <div className="flex items-center justify-between border-b border-border p-3">
          <span className="text-sm font-semibold">对话列表</span>
          <Button
            size="icon"
            variant="ghost"
            onClick={handleNewConversation}
            disabled={creating}
          >
            {creating ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Plus className="size-4" />
            )}
          </Button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-2">
          {conversations.length === 0 ? (
            <p className="p-4 text-center text-sm text-muted-foreground">
              暂无对话
            </p>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                className={cn(
                  "group flex w-full items-start gap-2.5 rounded-lg px-3 py-2.5 text-left transition-colors",
                  activeId === conv.id
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted"
                )}
              >
                <button
                  onClick={() => selectChat(conv.id)}
                  className="flex flex-1 items-start gap-2.5"
                >
                  <MessageSquare className="mt-0.5 size-4 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">
                      {conv.title}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatTime(conv.created_at)}
                    </div>
                  </div>
                </button>
                <button
                  onClick={() => handleDeleteChat(conv.id)}
                  className="mt-0.5 hidden shrink-0 text-muted-foreground hover:text-red-500 group-hover:block"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 右侧 - 对话内容 */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {/* 顶部栏 */}
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4">
          <div className="flex min-w-0 items-center">
            <Sparkles className="mr-2 size-4 shrink-0 text-primary" />
            <span className="truncate font-semibold">
              {activeChat?.title || "AI 研究助手"}
            </span>
          </div>
          {loadingLinkedPaper ? (
            <Button variant="ghost" size="sm" disabled className="gap-1">
              <Loader2 className="size-3.5 animate-spin" />
              读取论文链接...
            </Button>
          ) : linkedPaperUrl ? (
            <a
              href={linkedPaperUrl}
              target="_blank"
              rel="noopener noreferrer"
              title={linkedPaperTitle ? `打开论文：${linkedPaperTitle}` : "打开论文链接"}
            >
              <Button variant="default" size="sm" className="gap-1">
                <ExternalLink className="size-3.5" />
                跳转论文
              </Button>
            </a>
          ) : null}
        </div>

        {/* 消息区域 */}
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-4">
          {!activeChat || activeChat.messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
              <Bot className="mb-4 size-12" />
              <p className="text-lg font-medium">开始新的对话</p>
              <p className="mt-1 text-sm">
                在下方输入框输入问题，即可自动创建新对话
              </p>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-6">
              {activeChat.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={cn(
                    "flex gap-3",
                    msg.role === "user" ? "justify-end" : "justify-start"
                  )}
                >
                  {msg.role === "assistant" && (
                    <Avatar>
                      <AvatarFallback className="bg-primary/10 text-primary">
                        <Bot className="size-4" />
                      </AvatarFallback>
                    </Avatar>
                  )}
                  <div
                    className={cn(
                      "min-w-0 max-w-[85%] rounded-xl px-4 py-2.5 text-sm md:max-w-[80%]",
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    )}
                  >
                    <ChatMessageContent
                      content={msg.content}
                      isUser={msg.role === "user"}
                      highlightKeywords={msg.role === "assistant" ? highlightKeywords : []}
                    />
                    <div
                      className={cn(
                        "mt-1 text-xs",
                        msg.role === "user"
                          ? "text-primary-foreground/70"
                          : "text-muted-foreground"
                      )}
                    >
                      {new Date(msg.created_at).toLocaleTimeString("zh-CN", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </div>
                  {msg.role === "user" && (
                    <Avatar>
                      <AvatarFallback className="bg-secondary">
                        <User className="size-4" />
                      </AvatarFallback>
                    </Avatar>
                  )}
                </div>
              ))}

              {/* 流式输出中的 AI 回复 */}
              {sending && streamingContent && (
                <div className="flex gap-3 justify-start">
                  <Avatar>
                    <AvatarFallback className="bg-primary/10 text-primary">
                      <Bot className="size-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="bg-muted rounded-xl px-4 py-2.5 text-sm">
                    <ChatMessageContent
                      content={streamingContent}
                      isUser={false}
                      highlightKeywords={highlightKeywords}
                    />
                  </div>
                </div>
              )}

              {/* 等待 AI 响应中（还没收到内容时） */}
              {sending && !streamingContent && (
                <div className="flex gap-3 justify-start">
                  <Avatar>
                    <AvatarFallback className="bg-primary/10 text-primary">
                      <Bot className="size-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="bg-muted rounded-xl px-4 py-2.5 text-sm">
                    <Loader2 className="size-4 animate-spin" />
                  </div>
                </div>
              )}

              {/* 研究进度显示 */}
              {sending && isStreaming && currentStage !== "idle" && (
                <div className="flex gap-3 justify-start">
                  <Avatar>
                    <AvatarFallback className="bg-primary/10 text-primary">
                      <Zap className="size-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="bg-primary/5 border border-primary/20 rounded-xl px-4 py-3 max-w-[80%]">
                    <div className="flex items-center gap-2 mb-2">
                      <Loader2 className="size-3 animate-spin text-primary" />
                      <span className="text-xs font-medium text-primary">
                        {stageLabels[currentStage]}
                      </span>
                    </div>
                    {/* 进度条 */}
                    <div className="w-full bg-primary/10 rounded-full h-1.5">
                      <div
                        className="bg-primary h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <div className="flex justify-between mt-1">
                      <span className="text-[10px] text-muted-foreground">
                        {progress}%
                      </span>
                      <button
                        onClick={() => setShowProgress(!showProgress)}
                        className="text-[10px] text-muted-foreground hover:text-foreground flex items-center gap-0.5"
                      >
                        {showProgress ? (
                          <>
                            收起 <ChevronUp className="size-3" />
                          </>
                        ) : (
                          <>
                            展开 <ChevronDown className="size-3" />
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 输入区域 */}
        <div className="shrink-0 border-t border-border bg-background p-4 space-y-2">
          <div className="mx-auto flex max-w-3xl gap-2">
            <Input
              placeholder="输入你的问题..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              className="flex-1"
              disabled={sending || creating}
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || sending || creating}
            >
              <Send className="size-4" />
              {sending ? "生成中..." : "发送"}
            </Button>
          </div>

          {/* 快捷提示 */}
          {!activeChat || activeChat.messages.length === 0 ? (
            <div className="mx-auto flex max-w-3xl gap-2 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                className="gap-1"
                onClick={() => setInput("帮我找关于大语言模型最新进展的论文")}
                disabled={sending || creating}
              >
                <Sparkles className="size-3.5" />
                推荐论文
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1"
                onClick={() => setInput("最近有哪些关于多模态学习的论文？")}
                disabled={sending || creating}
              >
                <Search className="size-3.5" />
                搜索论文
              </Button>
            </div>
          ) : null}
        </div>


      </div>
    </div>
  );
}
