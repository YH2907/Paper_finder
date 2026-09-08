"use client";

/**
 * 研究上下文 - 集中管理论文推荐状态
 * 支持跨页面共享数据和流式进度跟踪
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";

// ── 类型定义 ──────────────────────────────────────────────

/** 流式事件类型 */
export interface StreamingEvent {
  type: string;
  stage?: string;
  content?: string;
  timestamp: string;
  research_id?: string;
  model?: string;
  error?: string;
  node_name?: string;
  node_count?: number;
  duration?: number;
}

/** 研究阶段 */
export type ResearchStage =
  | "idle"
  | "analyzing"
  | "searching"
  | "ranking"
  | "completing"
  | "completed"
  | "error";

/** 研究状态 */
export interface ResearchState {
  // 消息列表（跨页面共享）
  messages: ResearchMessage[];
  setMessages: (
    msgs: ResearchMessage[] | ((prev: ResearchMessage[]) => ResearchMessage[])
  ) => void;

  // 流式事件
  streamingEvents: StreamingEvent[];
  setStreamingEvents: (
    events:
      | StreamingEvent[]
      | ((prev: StreamingEvent[]) => StreamingEvent[])
  ) => void;

  // 当前研究阶段
  currentStage: ResearchStage;
  setCurrentStage: (stage: ResearchStage) => void;

  // 是否正在流式传输
  isStreaming: boolean;
  setIsStreaming: (streaming: boolean) => void;

  // 当前搜索查询
  currentQuery: string;
  setCurrentQuery: (query: string) => void;

  // 研究进度 (0-100)
  progress: number;
  setProgress: (progress: number) => void;

  // 流式内容
  streamingContent: string;
  setStreamingContent: (content: string) => void;

  // 研究结果（论文列表等）
  researchResult: ResearchResult | null;
  setResearchResult: (result: ResearchResult | null) => void;

  // 错误信息
  error: string | null;
  setError: (error: string | null) => void;

  // 清除所有状态
  resetResearch: () => void;
}

export interface ResearchMessage {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: string;
  sources?: string[];
}

export interface ResearchResult {
  papers: Array<{
    id: string;
    title: string;
    authors: string[];
    abstract: string;
    url: string;
    source: string;
    published_at: string | null;
  }>;
  analysis: {
    main_concepts: string[];
    research_objectives: string[];
    search_keywords: string[];
    summary: string;
  };
  total: number;
}

// ── Context ───────────────────────────────────────────────

const ResearchContext = createContext<ResearchState | undefined>(undefined);

// ── Hook ──────────────────────────────────────────────────

export function useResearchState(): ResearchState {
  const context = useContext(ResearchContext);
  if (!context) {
    throw new Error("useResearchState 必须在 ResearchProvider 内部使用");
  }
  return context;
}

// ── Provider ──────────────────────────────────────────────

export function ResearchProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ResearchMessage[]>([]);
  const [streamingEvents, setStreamingEvents] = useState<StreamingEvent[]>([]);
  const [currentStage, setCurrentStage] = useState<ResearchStage>("idle");
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentQuery, setCurrentQuery] = useState("");
  const [progress, setProgress] = useState(0);
  const [streamingContent, setStreamingContent] = useState("");
  const [researchResult, setResearchResult] = useState<ResearchResult | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);

  const resetResearch = useCallback(() => {
    setMessages([]);
    setStreamingEvents([]);
    setCurrentStage("idle");
    setIsStreaming(false);
    setCurrentQuery("");
    setProgress(0);
    setStreamingContent("");
    setResearchResult(null);
    setError(null);
  }, []);

  const value: ResearchState = {
    messages,
    setMessages,
    streamingEvents,
    setStreamingEvents,
    currentStage,
    setCurrentStage,
    isStreaming,
    setIsStreaming,
    currentQuery,
    setCurrentQuery,
    progress,
    setProgress,
    streamingContent,
    setStreamingContent,
    researchResult,
    setResearchResult,
    error,
    setError,
    resetResearch,
  };

  return (
    <ResearchContext.Provider value={value}>
      {children}
    </ResearchContext.Provider>
  );
}
