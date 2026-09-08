"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight,
  Search,
  Loader2,
  RefreshCw,
  Database,
  Globe,
  Filter,
} from "lucide-react";
import PaperCard from "@/components/papers/PaperCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  getPapers,
  getTopics,
  bookmarkPaper,
  unbookmarkPaper,
  markPaperRead,
  type Paper,
  type Topic,
} from "@/lib/api";

const sourceColors: Record<string, string> = {
  arxiv: "bg-blue-100 text-blue-700",
  semantic_scholar: "bg-green-100 text-green-700",
  google_scholar: "bg-yellow-100 text-yellow-700",
  pubmed: "bg-red-100 text-red-700",
};

function getSourceColor(source: string) {
  const key = source.toLowerCase().replace(/[^a-z]/g, "_");
  return sourceColors[key] || "bg-muted text-muted-foreground";
}

function getSourceLabel(source: string) {
  const map: Record<string, string> = {
    arxiv: "arXiv",
    semantic_scholar: "Semantic Scholar",
    google_scholar: "Google Scholar",
    pubmed: "PubMed",
  };
  return map[source.toLowerCase().replace(/[^a-z]/g, "_")] || source;
}

export default function PapersPage() {
  const router = useRouter();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [selectedTopic, setSelectedTopic] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [strictSearch, setStrictSearch] = useState(false);

  const perPage = 10;
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const searchKeywords = useMemo(() => {
    return search
      .split(/[，,;；、\s]+/)
      .map((kw) => kw.trim())
      .filter((kw) => kw.length > 0);
  }, [search]);

  // Debounced search
  const handleSearchInput = useCallback((value: string) => {
    setSearchInput(value);
    if (value.trim()) setSearching(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearch(value);
      setCurrentPage(1);
    }, 400);
  }, []);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  // Load topics
  useEffect(() => {
    async function loadTopics() {
      try {
        const res = await getTopics();
        if (res.success) setTopics(res.data);
      } catch {
        // ignore
      }
    }
    loadTopics();
  }, []);

  // Load papers
  const loadPapers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getPapers(
        currentPage,
        perPage,
        selectedTopic || undefined,
        search || undefined,
        strictSearch
      );
      if (res.success) {
        setPapers(res.data.papers);
        setTotal(res.data.total);
        setTotalPages(Math.ceil(res.data.total / perPage));
      }
    } catch {
      setError("加载论文失败");
    } finally {
      setLoading(false);
      setSearching(false);
    }
  }, [currentPage, selectedTopic, search, strictSearch]);

  useEffect(() => {
    loadPapers();
  }, [loadPapers]);

  // Refresh handler
  const handleRefresh = async () => {
    setRefreshing(true);
    await loadPapers();
    setRefreshing(false);
  };

  const handleBookmark = async (paperId: string) => {
    try {
      const paper = papers.find((p) => p.id === paperId);
      const isCurrentlyBookmarked = paper?.is_bookmarked ?? false;
      if (isCurrentlyBookmarked) {
        await unbookmarkPaper(paperId);
      } else {
        await bookmarkPaper(paperId);
      }
      // Update local state
      setPapers((prev) =>
        prev.map((p) =>
          p.id === paperId ? { ...p, is_bookmarked: !isCurrentlyBookmarked } : p
        )
      );
    } catch {
      // ignore
    }
  };

  const handleMarkRead = async (paperId: string) => {
    try {
      await markPaperRead(paperId);
      // Update local state
      setPapers((prev) =>
        prev.map((p) =>
          p.id === paperId ? { ...p, is_read: true } : p
        )
      );
    } catch {
      // ignore
    }
  };

  const handlePaperClick = (paperId: string) => {
    router.push(`/papers/${paperId}`);
  };

  const handleTopicFilter = (topicId: string) => {
    setSelectedTopic(topicId === selectedTopic ? "" : topicId);
    setCurrentPage(1);
  };

  // Search progress bar
  const isLoadingProgress = loading && search;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">论文列表</h2>
          <p className="mt-1 text-muted-foreground">
            浏览和管理您关注的所有论文
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <RefreshCw className="size-4" />
          )}
          {refreshing ? "刷新中..." : "刷新"}
        </Button>
      </div>

      {/* Search progress bar */}
      {(isLoadingProgress || searching) && (
        <div className="overflow-hidden rounded-full bg-muted">
          <div className="h-1 w-full animate-pulse bg-gradient-to-r from-primary/20 via-primary/50 to-primary/20" />
        </div>
      )}

      {/* Search & Filters */}
      <div className="space-y-3 rounded-xl border bg-card p-4">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="搜索论文标题或摘要..."
              value={searchInput}
              onChange={(e) => handleSearchInput(e.target.value)}
              className="pl-9"
            />
            {searching && (
              <Loader2 className="absolute right-3 top-1/2 size-4 -translate-y-1/2 animate-spin text-primary" />
            )}
          </div>
          <Button
            type="button"
            variant={strictSearch ? "default" : "outline"}
            size="sm"
            className="gap-1"
            onClick={() => {
              setStrictSearch((prev) => !prev);
              setCurrentPage(1);
            }}
            title="严格搜索开启后，所有关键词都需要命中标题或摘要"
          >
            <Filter className="size-4" />
            严格搜索
          </Button>
        </div>
        {strictSearch && (
          <p className="text-xs text-muted-foreground">
            已开启严格搜索：需要命中全部关键词
          </p>
        )}

        {/* Source summary tags */}
        {papers.length > 0 && !loading && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Database className="size-3.5" />
            <span>数据来源：</span>
            {Array.from(new Set(papers.map((p) => p.source))).map((source) => (
              <span
                key={source}
                className={cn(
                  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium",
                  getSourceColor(source)
                )}
              >
                <Globe className="size-3" />
                {getSourceLabel(source)}
              </span>
            ))}
          </div>
        )}

        {topics.length > 0 && (
          <>
            <div className="flex items-center gap-2 text-sm font-medium">
              <SlidersHorizontal className="size-4" />
              按主题筛选
            </div>
            <div className="flex flex-wrap gap-1.5">
              <Badge
                variant={selectedTopic === "" ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => handleTopicFilter("")}
              >
                全部
              </Badge>
              {topics.map((topic) => (
                <Badge
                  key={topic.id}
                  variant={selectedTopic === topic.id ? "default" : "outline"}
                  className="cursor-pointer"
                  onClick={() => handleTopicFilter(topic.id)}
                >
                  {topic.name}
                </Badge>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Paper list */}
      {loading ? (
        <div className="flex h-32 items-center justify-center">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="flex h-32 items-center justify-center">
          <p className="text-red-500">{error}</p>
        </div>
      ) : papers.length === 0 ? (
        <div className="flex flex-col h-32 items-center justify-center gap-2">
          <p className="text-muted-foreground">暂无论文数据</p>
          {search && (
            <p className="text-xs text-muted-foreground">
              未找到与「{search}」相关的论文
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {papers.map((paper) => (
            <div
              key={paper.id}
              className="cursor-pointer"
              onClick={() => handlePaperClick(paper.id)}
            >
              <PaperCard
                paper={paper}
                isBookmarked={paper.is_bookmarked}
                isRead={paper.is_read}
                onBookmark={handleBookmark}
                onMarkRead={handleMarkRead}
                highlightKeywords={searchKeywords}
              />
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="icon"
            disabled={currentPage === 1}
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft className="size-4" />
          </Button>
          {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
            let page: number;
            if (totalPages <= 7) {
              page = i + 1;
            } else if (currentPage <= 4) {
              page = i + 1;
            } else if (currentPage >= totalPages - 3) {
              page = totalPages - 6 + i;
            } else {
              page = currentPage - 3 + i;
            }
            // Show ellipsis
            if (totalPages > 7 && i > 0) {
              const prevPage =
                i === 0
                  ? 0
                  : totalPages <= 7
                    ? i
                    : currentPage <= 4
                      ? i
                      : currentPage >= totalPages - 3
                        ? totalPages - 7 + i
                        : currentPage - 4 + i;
              // We'll just render buttons; skip true ellipsis for simplicity
            }
            return (
              <Button
                key={page}
                variant={currentPage === page ? "default" : "outline"}
                size="sm"
                className={cn(
                  "min-w-[36px]",
                  currentPage === page && "pointer-events-none"
                )}
                onClick={() => setCurrentPage(page)}
              >
                {page}
              </Button>
            );
          })}
          <Button
            variant="outline"
            size="icon"
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
          >
            <ChevronRight className="size-4" />
          </Button>
          <span className="ml-2 text-sm text-muted-foreground">
            共 {total} 篇
          </span>
        </div>
      )}
    </div>
  );
}
