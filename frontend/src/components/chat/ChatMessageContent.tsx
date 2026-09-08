"use client";

import { useState, useEffect, useMemo } from "react";
import { FileText, Sparkles, Bookmark, BookmarkCheck, Loader2, ArrowRight, Copy } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { parsePaperRefs, extractPaperId } from "@/lib/paper-parser";
import { searchPapers, bookmarkPaper, unbookmarkPaper, type Paper } from "@/lib/api";

interface ChatMessageContentProps {
  content: string;
  isUser?: boolean;
  highlightKeywords?: string[];
}

interface CachedPaper {
  data: Paper | null;
  loaded: boolean;
}

/**
 * 渲染消息内容，自动解析论文引用并显示为完整的论文卡片
 */
export default function ChatMessageContent({
  content,
  isUser = false,
  highlightKeywords = [],
}: ChatMessageContentProps) {
  const [paperCache, setPaperCache] = useState<Record<string, CachedPaper>>({});
  const [bookmarkedPapers, setBookmarkedPapers] = useState<Set<string>>(new Set());
  const [loadingPapers, setLoadingPapers] = useState<Set<string>>(new Set());

  const paperRefs = useMemo(() => !isUser ? parsePaperRefs(content) : [], [content, isUser]);

  // 自动加载论文信息
  useEffect(() => {
    if (isUser || paperRefs.length === 0) return;

    paperRefs.forEach(ref => {
      if (ref.url && !paperCache[ref.url]?.loaded && !loadingPapers.has(ref.url)) {
        loadPaperInfo(ref.url, ref.title);
      }
    });
  }, [paperRefs, paperCache, loadingPapers, isUser]);

  const loadPaperInfo = async (url: string, title?: string) => {
    const paperId = extractPaperId(url);
    const query = paperId || title?.trim() || url;
    setLoadingPapers(prev => new Set([...prev, url]));

    try {
      const result = await searchPapers(query, 1);
      
      if (result.success && result.data && result.data.length > 0) {
        const paper = result.data[0];
        setPaperCache(prev => ({ 
          ...prev, 
          [url]: { data: paper, loaded: true } 
        }));
      } else {
        setPaperCache(prev => ({ 
          ...prev, 
          [url]: { data: null, loaded: true } 
        }));
      }
    } catch (error) {
      console.error("加载论文信息失败:", error);
      setPaperCache(prev => ({ 
        ...prev, 
        [url]: { data: null, loaded: true } 
      }));
    } finally {
      setLoadingPapers(prev => {
        const next = new Set(prev);
        next.delete(url);
        return next;
      });
    }
  };

  if (isUser) {
    return (
      <div className="whitespace-pre-wrap">{content}</div>
    );
  }

  if (paperRefs.length === 0) {
    return (
      <div className="whitespace-pre-wrap">{content}</div>
    );
  }

  // 将文本分段
  const segments: Array<{ type: "text" | "paper"; text: string; url?: string; title?: string }> = [];
  let lastEnd = 0;

  for (const ref of paperRefs) {
    if (ref.start > lastEnd) {
      segments.push({
        type: "text",
        text: content.slice(lastEnd, ref.start),
      });
    }
    segments.push({
      type: "paper",
      text: content.slice(ref.start, ref.end),
      url: ref.url,
      title: ref.title,
    });
    lastEnd = ref.end;
  }

  if (lastEnd < content.length) {
    segments.push({
      type: "text",
      text: content.slice(lastEnd),
    });
  }

  const handleBookmark = async (e: React.MouseEvent, url: string) => {
    e.preventDefault();
    e.stopPropagation();

    const cached = paperCache[url];
    if (!cached?.data) return;

    try {
      setLoadingPapers(prev => new Set([...prev, url]));
      const paper = cached.data;
      
      if (bookmarkedPapers.has(paper.id)) {
        await unbookmarkPaper(paper.id);
        setBookmarkedPapers(prev => {
          const next = new Set(prev);
          next.delete(paper.id);
          return next;
        });
      } else {
        await bookmarkPaper(paper.id);
        setBookmarkedPapers(prev => new Set([...prev, paper.id]));
      }
    } catch (error) {
      console.error("更新论文收藏状态失败:", error);
    } finally {
      setLoadingPapers(prev => {
        const next = new Set(prev);
        next.delete(url);
        return next;
      });
    }
  };

  const renderHighlightedText = (text: string) => {
    if (!text || highlightKeywords.length === 0) {
      return <>{text}</>;
    }

    const escaped = highlightKeywords
      .map((kw) => kw.trim())
      .filter((kw) => kw.length > 0)
      .map((kw) => kw.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));

    if (escaped.length === 0) {
      return <>{text}</>;
    }

    const regex = new RegExp(`(${escaped.join("|")})`, "gi");
    const parts = text.split(regex);

    return (
      <>
        {parts.map((part, index) => {
          const matched = highlightKeywords.some((kw) => part.toLowerCase() === kw.toLowerCase());
          if (!matched) {
            return <span key={`${part}-${index}`}>{part}</span>;
          }
          return (
            <mark
              key={`${part}-${index}`}
              className="rounded bg-amber-200/80 px-0.5 text-amber-900"
            >
              {part}
            </mark>
          );
        })}
      </>
    );
  };

  return (
    <div className="space-y-3">
      {segments.map((segment, i) => {
        if (segment.type === "text") {
          return (
            <span key={i} className="whitespace-pre-wrap">
              {segment.text}
            </span>
          );
        }
        
        const cached = segment.url ? paperCache[segment.url] : null;
        const paper = cached?.data;
        const isLoading = !!(segment.url && loadingPapers.has(segment.url));
        const isBookmarked = paper && bookmarkedPapers.has(paper.id);
        const preferredUrl = paper?.url?.trim() || segment.url || "";
        const isSearchLink = preferredUrl.includes("bing.com/search");

        const hostLabel = (() => {
          if (!preferredUrl) return "";
          try {
            return new URL(preferredUrl).hostname;
          } catch {
            return preferredUrl;
          }
        })();

        return (
          <div key={i}>
            {/* 论文卡片 */}
            <div
              className={cn(
                "rounded-lg border bg-card p-3 transition-all hover:shadow-md hover:border-purple-300",
                "dark:hover:border-purple-700",
                isLoading && "opacity-75"
              )}
            >
              <div className="flex items-start gap-3">
                {/* Icon */}
                <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/50 mt-0.5">
                  <FileText className="size-5 text-purple-600 dark:text-purple-400" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="secondary" className="gap-1 shrink-0">
                      <Sparkles className="size-3" />
                      推荐论文
                    </Badge>
                    {isLoading && (
                      <Loader2 className="size-3 animate-spin text-muted-foreground" />
                    )}
                  </div>
                  
                  {segment.title ? (
                    <p className="font-medium text-sm text-foreground line-clamp-2 mb-1">
                      {renderHighlightedText(segment.title)}
                    </p>
                  ) : (
                    <p className="text-sm text-muted-foreground mb-1 truncate">
                      {segment.url}
                    </p>
                  )}

                  {paper && (
                    <>
                      <p className="text-xs text-muted-foreground line-clamp-1 mb-1">
                        {paper.authors?.slice(0, 3).join(", ") || "未知作者"}
                        {paper.authors && paper.authors.length > 3 ? "..." : ""}
                      </p>
                      {paper.abstract && (
                        <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                          {paper.abstract}
                        </p>
                      )}
                    </>
                  )}

                  <p className="text-xs text-muted-foreground">
                    {hostLabel}
                    {paper?.source && ` · ${paper.source}`}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex flex-col items-center gap-2 shrink-0">
                  {paper && (
                    <button
                      onClick={(e) => handleBookmark(e, segment.url!)}
                      disabled={isLoading}
                      className="p-1.5 rounded-lg hover:bg-muted transition-colors"
                      title={isBookmarked ? "取消收藏" : "收藏论文"}
                    >
                      {isLoading ? (
                        <Loader2 className="size-4 animate-spin text-muted-foreground" />
                      ) : isBookmarked ? (
                        <BookmarkCheck className="size-4 text-amber-500" />
                      ) : (
                        <Bookmark className="size-4 text-muted-foreground hover:text-foreground" />
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* 跳转按钮 - 明显的查看论文按钮 */}
              <div className="mt-3 flex justify-end gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="gap-2"
                  onClick={async (e) => {
                    e.stopPropagation();
                    if (!preferredUrl) return;
                    try {
                      await navigator.clipboard.writeText(preferredUrl);
                    } catch {
                      // ignore clipboard errors in restricted contexts
                    }
                  }}
                >
                  复制链接
                  <Copy className="size-3.5" />
                </Button>

                <a
                  href={preferredUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Button size="sm" className="gap-2 bg-purple-600 hover:bg-purple-700 text-white">
                    {isSearchLink ? "搜索论文网站" : "前往论文原文"}
                    <ArrowRight className="size-3.5" />
                  </Button>
                </a>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
