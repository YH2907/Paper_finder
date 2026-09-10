"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import {
  getRecommendedPapers,
  getTopics,
  getBookmarkedPapers,
  type Paper,
  type Topic,
} from "@/lib/api";
import {
  TrendingUp,
  BookOpen,
  Bookmark,
  Clock,
  ArrowRight,
  Sparkles,
  RefreshCw,
  Loader2,
  Search,
  X,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// 高亮关键词组件
function HighlightText({ text, keywords }: { text: string; keywords: string[] }) {
  if (!keywords.length || !text) return <>{text}</>;
  
  const escapedKeywords = keywords.map(kw => kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const regex = new RegExp(`(${escapedKeywords.join("|")})`, "gi");
  const parts = text.split(regex);
  
  return (
    <>
      {parts.map((part, i) => {
        const isMatch = keywords.some(kw => part.toLowerCase() === kw.toLowerCase());
        return isMatch ? (
          <mark key={i} className="bg-yellow-200 text-yellow-900 px-0.5 rounded">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        );
      })}
    </>
  );
}

export default function HomePage() {
  const { user, isAuthenticated } = useAuth();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [bookmarkCount, setBookmarkCount] = useState(0);
  const [readCount, setReadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [newPaperIds, setNewPaperIds] = useState<Set<string>>(new Set());
  const [filterQuery, setFilterQuery] = useState("");

  async function loadData(clearHistory = false) {
    setLoading(true);
    try {
      const [papersRes, topicsRes] = await Promise.all([
        getRecommendedPapers(10, false, false, clearHistory),
        getTopics(),
      ]);

      if (papersRes.success) {
        const newPapers = papersRes.data || [];
        const newIds = newPapers.filter((p) => p.is_new).map((p) => p.id);
        setNewPaperIds(new Set(newIds));
        setPapers(newPapers);
        setReadCount(newPapers.filter((p) => p.is_read).length);
      }

      if (topicsRes.success) setTopics(topicsRes.data || []);

      getBookmarkedPapers(1, 100)
        .then((bookmarksRes) => {
          if (bookmarksRes.success) setBookmarkCount(bookmarksRes.data.total);
        })
        .catch(() => {});
    } catch (error) {
      console.error("加载数据失败:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!isAuthenticated) return;
    queueMicrotask(() => void loadData());
  }, [isAuthenticated]);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      const papersRes = await getRecommendedPapers(10, false, false, true);
      if (papersRes.success) {
        const newPapers = papersRes.data || [];
        const newIds = newPapers.filter((p) => p.is_new).map((p) => p.id);
        setNewPaperIds(new Set(newIds));
        setPapers(newPapers);
        setReadCount(newPapers.filter((p) => p.is_read).length);
      }
    } catch (error) {
      console.error("刷新失败:", error);
    } finally {
      setRefreshing(false);
    }
  }

  // 更准确的本地过滤：支持模糊匹配和多关键词
  const filteredPapers = useMemo(() => {
    if (!filterQuery.trim()) return papers;
    
    const keywords = filterQuery
      .toLowerCase()
      .split(/[,，;；、\s]+/)
      .filter(kw => kw.length > 0);
    
    if (keywords.length === 0) return papers;

    return papers
      .map(paper => {
        const title = (paper.title || "").toLowerCase();
        const abstract = (paper.abstract || "").toLowerCase();
        const authors = (paper.authors || []).join(" ").toLowerCase();
        // 计算匹配分数
        let score = 0;
        let matchedKeywords = 0;
        
        for (const kw of keywords) {
          if (title.includes(kw)) {
            score += 10; // 标题匹配权重最高
            matchedKeywords++;
          } else if (abstract.includes(kw)) {
            score += 5; // 摘要匹配
            matchedKeywords++;
          } else if (authors.includes(kw)) {
            score += 2; // 作者匹配
            matchedKeywords++;
          }
        }
        
        // 必须匹配至少一个关键词
        if (matchedKeywords === 0) return null;
        
        // 多关键词匹配加分
        if (matchedKeywords > 1) score += matchedKeywords * 3;
        
        return { paper, score };
      })
      .filter((item): item is { paper: Paper; score: number } => item !== null)
      .sort((a, b) => b.score - a.score)
      .map(item => item.paper);
  }, [papers, filterQuery]);

  // 解析过滤关键词用于高亮
  const filterKeywords = useMemo(() => {
    return filterQuery
      .split(/[,，;；、\s]+/)
      .filter(kw => kw.length > 0);
  }, [filterQuery]);

  const stats = [
    { label: "推荐论文", value: papers.length, icon: TrendingUp, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "研究主题", value: topics.length, icon: BookOpen, color: "text-green-600", bg: "bg-green-50" },
    { label: "已收藏", value: bookmarkCount, icon: Bookmark, color: "text-purple-600", bg: "bg-purple-50" },
    { label: "已读", value: readCount, icon: Clock, color: "text-orange-600", bg: "bg-orange-50" },
  ];

  return (
    <div className="space-y-6 p-6">
      <div>
        <h2 className="text-2xl font-bold">
          👋 {isAuthenticated ? `欢迎回来，${user?.name || "研究员"}` : "欢迎使用 Paper Finder"}
        </h2>
        <p className="mt-1 text-muted-foreground">
          {isAuthenticated ? "基于您的研究主题，为您推荐最新论文。" : "请登录以查看您的论文推荐。"}
        </p>
      </div>

      {isAuthenticated && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <Card key={stat.label}>
              <CardContent className="flex items-center gap-4 py-4">
                <div className={`flex size-12 items-center justify-center rounded-xl ${stat.bg}`}>
                  <stat.icon className={`size-5 ${stat.color}`} />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stat.value}</p>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {isAuthenticated && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-lg font-semibold">
              <Sparkles className="size-5 text-purple-600" />
              论文推荐
            </h3>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
                {refreshing ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
                {refreshing ? "刷新中..." : "刷新推荐"}
              </Button>
              <Link href="/papers">
                <Button variant="ghost" size="sm" className="gap-1">
                  查看全部 <ArrowRight className="size-4" />
                </Button>
              </Link>
            </div>
          </div>

          {/* 本地过滤搜索框 */}
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="在推荐论文中搜索关键词（支持多关键词，如：AGV deadlock）"
                value={filterQuery}
                onChange={(e) => setFilterQuery(e.target.value)}
                className="pl-9 pr-9"
              />
              {filterQuery && (
                <button
                  onClick={() => setFilterQuery("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="size-4" />
                </button>
              )}
            </div>
            {filterQuery && (
              <p className="mt-1 text-xs text-muted-foreground">
                找到 {filteredPapers.length} 篇匹配论文（关键词高亮显示）
              </p>
            )}
          </div>

          <div className="space-y-4">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="size-6 animate-spin text-muted-foreground" />
              </div>
            ) : filteredPapers.length > 0 ? (
              filteredPapers.map((paper) => (
                <Link key={paper.id} href={`/papers/${paper.id}`}>
                  <Card className={`transition-shadow hover:shadow-md cursor-pointer ${newPaperIds.has(paper.id) ? "border-purple-300 bg-purple-50/40" : ""}`}>
                    <CardHeader>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 space-y-1">
                          <CardTitle className="text-base leading-snug">
                            <HighlightText text={paper.title} keywords={filterKeywords} />
                          </CardTitle>
                          <p className="text-xs text-muted-foreground">
                            {paper.source} · {paper.published_at ? new Date(paper.published_at).toLocaleDateString() : "未知日期"}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          {newPaperIds.has(paper.id) && (
                            <Badge className="shrink-0 gap-1 bg-purple-600 text-white">
                              <Sparkles className="size-3" />
                              新推送
                            </Badge>
                          )}
                          <Badge variant="secondary" className="shrink-0">{paper.source}</Badge>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {paper.abstract && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          <HighlightText text={paper.abstract} keywords={filterKeywords} />
                        </p>
                      )}
                    </CardContent>
                  </Card>
                </Link>
              ))
            ) : filterQuery ? (
              <div className="text-center py-8 text-muted-foreground">
                没有找到匹配「{filterQuery}」的论文
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">暂无论文推荐，请先添加研究主题。</div>
            )}
          </div>
        </div>
      )}

      {isAuthenticated && topics.length > 0 && (
        <div>
          <h3 className="mb-4 text-lg font-semibold">🔬 活跃研究主题</h3>
          <div className="flex flex-wrap gap-2">
            {topics.map((topic) => (
              <Badge key={topic.id} variant="secondary" className="cursor-pointer px-3 py-1 text-sm transition-colors hover:bg-purple-100 hover:text-purple-700">
                {topic.name}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {!isAuthenticated && !loading && (
        <div className="text-center py-12">
          <h3 className="text-lg font-semibold mb-2">开始使用 Paper Finder</h3>
          <p className="text-muted-foreground mb-4">登录后即可查看论文推荐、管理研究主题。</p>
          <div className="flex gap-4 justify-center">
            <Link href="/login"><Button>登录</Button></Link>
            <Link href="/register"><Button variant="outline">注册</Button></Link>
          </div>
        </div>
      )}
    </div>
  );
}
