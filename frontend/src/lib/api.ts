export interface SimplePaper {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  url: string;
  source: string;
  published_at: string | null;
  doi: string | null;
}
const rawApiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_BASE = rawApiBase.endsWith("/api/v1")
  ? rawApiBase
  : `${rawApiBase.replace(/\/$/, "")}/api/v1`;

// ── Types ──────────────────────────────────────────────────

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  created_at: string;
}

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  url: string;
  doi: string | null;
  source: string;
  published_at: string | null;
  ai_summary: string | null;
  ai_problem_solved: string | null;
  is_bookmarked: boolean;
  is_read: boolean;
  is_new: boolean;
}

export interface PaperListData {
  papers: Paper[];
  total: number;
  page: number;
  per_page: number;
}

export interface Topic {
  id: string;
  name: string;
  keywords: string[];
  exclude_keywords: string[];
  description: string | null;
  problem_statement: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TopicCreate {
  name: string;
  keywords: string[];
  exclude_keywords: string[];
  description?: string;
  problem_statement?: string;
}

export interface TopicUpdate {
  name?: string;
  keywords?: string[];
  exclude_keywords?: string[];
  description?: string;
  problem_statement?: string;
  is_active?: boolean;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface Chat {
  id: string;
  title: string;
  paper_id: string | null;
  created_at: string;
  messages: Message[];
}

export interface ChatListItem {
  id: string;
  title: string;
  paper_id: string | null;
  created_at: string;
  last_message: string | null;
}

export interface Token {
  access_token: string;
  refresh_token: string | null;
  token_type: string;
}

export interface PushSettings {
  push_enabled: boolean;
  push_frequency: string;
  push_time: string;
  push_count: number;
}

// ── Token Management ───────────────────────────────────────

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function setToken(token: string): void {
  localStorage.setItem("token", token);
}

export function removeToken(): void {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
}

// ── HTTP Client ────────────────────────────────────────────

class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json();

  if (!response.ok) {
    throw new ApiError(response.status, data.detail || "请求失败");
  }

  return data;
}

// ── Auth API ───────────────────────────────────────────────

export async function login(
  email: string,
  password: string
): Promise<ApiResponse<Token>> {
  return request<ApiResponse<Token>>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function register(
  email: string,
  name: string,
  password: string
): Promise<ApiResponse<User>> {
  return request<ApiResponse<User>>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, name, password }),
  });
}

export async function getMe(): Promise<ApiResponse<User>> {
  return request<ApiResponse<User>>("/auth/me");
}

// ── User API ───────────────────────────────────────────────

export async function updateUser(data: {
  name?: string;
  avatar_url?: string;
}): Promise<ApiResponse<User>> {
  return request<ApiResponse<User>>("/users/me", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// ── Papers API ─────────────────────────────────────────────

export async function getPapers(
  page = 1,
  perPage = 20,
  topicId?: string,
  search?: string,
  matchAll = false
): Promise<ApiResponse<PaperListData>> {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  if (topicId) params.set("topic_id", topicId);
  if (search) params.set("search", search);
  params.set("match_all", String(matchAll));

  return request<ApiResponse<PaperListData>>(`/papers/?${params.toString()}`);
}

export async function getPaper(
  paperId: string
): Promise<ApiResponse<Paper>> {
  return request<ApiResponse<Paper>>(`/papers/${paperId}`);
}

export async function getRecommendedPapers(
  limit = 10,
  online = true,
  onlyUnseen = false,
  clearHistory = false
): Promise<ApiResponse<Paper[]>> {
  return request<ApiResponse<Paper[]>>(
    `/papers/recommended?limit=${limit}&online=${online}&only_unseen=${onlyUnseen}&clear_history=${clearHistory}`
  );
}

export async function searchPapers(
  query: string,
  limit = 20,
  online = false
): Promise<ApiResponse<Paper[]>> {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
    online: String(online),
  });
  return request<ApiResponse<Paper[]>>(
    `/papers/search?${params.toString()}`
  );
}

export async function bookmarkPaper(
  paperId: string
): Promise<ApiResponse<null>> {
  return request<ApiResponse<null>>(`/papers/${paperId}/bookmark`, {
    method: "POST",
  });
}

export async function unbookmarkPaper(
  paperId: string
): Promise<ApiResponse<null>> {
  return request<ApiResponse<null>>(`/papers/${paperId}/bookmark`, {
    method: "DELETE",
  });
}

export async function markPaperRead(
  paperId: string
): Promise<ApiResponse<null>> {
  return request<ApiResponse<null>>(`/papers/${paperId}/read`, {
    method: "POST",
  });
}

export async function getBookmarkedPapers(
  page = 1,
  perPage = 20
): Promise<ApiResponse<PaperListData>> {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  return request<ApiResponse<PaperListData>>(
    `/papers/bookmarks?${params.toString()}`
  );
}

// ── Topics API ─────────────────────────────────────────────

export async function getTopics(): Promise<ApiResponse<Topic[]>> {
  return request<ApiResponse<Topic[]>>("/topics/");
}

export async function createTopic(
  topic: TopicCreate
): Promise<ApiResponse<Topic>> {
  return request<ApiResponse<Topic>>("/topics/", {
    method: "POST",
    body: JSON.stringify(topic),
  });
}

export async function updateTopic(
  topicId: string,
  topic: TopicUpdate
): Promise<ApiResponse<Topic>> {
  return request<ApiResponse<Topic>>(`/topics/${topicId}`, {
    method: "PUT",
    body: JSON.stringify(topic),
  });
}

export async function deleteTopic(topicId: string): Promise<void> {
  return request<void>(`/topics/${topicId}`, {
    method: "DELETE",
  });
}

// ── Chat API ───────────────────────────────────────────────

export async function getChats(): Promise<ApiResponse<ChatListItem[]>> {
  return request<ApiResponse<ChatListItem[]>>("/chats/");
}

export async function createChat(
  title: string,
  paperId?: string
): Promise<ApiResponse<Chat>> {
  return request<ApiResponse<Chat>>("/chats/", {
    method: "POST",
    body: JSON.stringify({ title, paper_id: paperId || null }),
  });
}

export async function getChat(
  chatId: string
): Promise<ApiResponse<Chat>> {
  return request<ApiResponse<Chat>>(`/chats/${chatId}`);
}

export async function sendMessage(
  chatId: string,
  content: string
): Promise<ApiResponse<Message>> {
  return request<ApiResponse<Message>>(`/chats/${chatId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

/**
 * 流式发送消息，使用 SSE (Server-Sent Events)
 *
 * @param chatId - 对话 ID
 * @param content - 消息内容
 * @param onToken - 收到文本片段时的回调
 * @param onDone - 流结束时的回调
 * @param onError - 出错时的回调
 * @returns AbortController（可用于取消流式请求）
 */
export function sendMessageStream(
  chatId: string,
  content: string,
  onToken: (token: string) => void,
  onDone: (messageId: string) => void,
  onError: (error: string) => void
): AbortController {
  const token = getToken();
  const controller = new AbortController();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  fetch(`${API_BASE}/chats/${chatId}/messages/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({ content }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        onError(errorData.detail || `请求失败 (${response.status})`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        onError("无法读取流式响应");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const dataStr = line.slice(6);
          if (!dataStr.trim()) continue;

          try {
            const data = JSON.parse(dataStr);
            if (data.type === "token") {
              onToken(data.content);
            } else if (data.type === "done") {
              onDone(data.message_id);
            } else if (data.type === "error") {
              onError(data.content);
            }
          } catch {
            // 忽略解析错误
          }
        }
      }

      // 处理 buffer 中剩余的数据
      if (buffer.startsWith("data: ")) {
        try {
          const data = JSON.parse(buffer.slice(6));
          if (data.type === "token") {
            onToken(data.content);
          } else if (data.type === "done") {
            onDone(data.message_id);
          } else if (data.type === "error") {
            onError(data.content);
          }
        } catch {
          // 忽略
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(String(err));
      }
    });

  return controller;
}

export async function deleteChat(chatId: string): Promise<void> {
  return request<void>(`/chats/${chatId}`, {
    method: "DELETE",
  });
}

// ── Push Settings API ──────────────────────────────────────

export async function getPushSettings(): Promise<ApiResponse<PushSettings>> {
  return request<ApiResponse<PushSettings>>("/settings/push");
}

export async function updatePushSettings(
  settings: Partial<PushSettings>
): Promise<ApiResponse<PushSettings>> {
  return request<ApiResponse<PushSettings>>("/settings/push", {
    method: "PUT",
    body: JSON.stringify(settings),
  });
}

// ── Deep Research API ──────────────────────────────────────

export interface DeepResearchAnalysis {
  main_concepts: string[];
  research_objectives: string[];
  key_problems: string[];
  search_keywords: string[];
  summary: string;
}

export interface SimplePaper {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  url: string;
  source: string;
  published_at: string | null;
  doi: string | null;
}

export interface DeepResearchResult {
  success: boolean;
  analysis: DeepResearchAnalysis;
  papers: SimplePaper[];
  total: number;
  message: string;
}

export async function deepResearch(
  query: string,
  topicId?: string,
  limit: number = 20
): Promise<ApiResponse<DeepResearchResult>> {
  const params = new URLSearchParams({
    query,
    limit: String(limit),
  });
  if (topicId) params.set("topic_id", topicId);

  return request<ApiResponse<DeepResearchResult>>(
    `/deep-research/?${params.toString()}`,
    {
      method: "POST",
    }
  );
}
