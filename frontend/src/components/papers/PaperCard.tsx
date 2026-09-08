"use client";

import {
  ExternalLink,
  Bookmark,
  BookmarkCheck,
  MessageSquare,
  CheckCircle2,
  Sparkles,
  BellRing,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface PaperData {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  url: string;
  source: string;
  published_at: string | null;
  ai_summary: string | null;
  ai_problem_solved: string | null;
  is_new?: boolean;
}

interface PaperCardProps {
  paper: PaperData;
  isBookmarked?: boolean;
  isRead?: boolean;
  onBookmark?: (id: string) => void;
  onMarkRead?: (id: string) => void;
  highlightKeywords?: string[];
}

function HighlightTitle({ text, keywords }: { text: string; keywords: string[] }) {
  if (!text || keywords.length === 0) {
    return <>{text}</>;
  }

  const escaped = keywords
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
        const matched = keywords.some((kw) => part.toLowerCase() === kw.toLowerCase());
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
}

export default function PaperCard({
  paper,
  isBookmarked = false,
  isRead = false,
  onBookmark,
  onMarkRead,
  highlightKeywords = [],
}: PaperCardProps) {
  const authorsStr = paper.authors?.join(", ") || "未知作者";
  const dateStr = paper.published_at
    ? new Date(paper.published_at).toLocaleDateString("zh-CN")
    : "未知日期";

  const handleBookmark = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onBookmark?.(paper.id);
  };

  const handleMarkRead = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onMarkRead?.(paper.id);
  };

  return (
    <Card
      className={cn(
        "transition-all hover:shadow-md",
        paper.is_new && "border-purple-300 bg-purple-50/40",
        isRead && "opacity-60 bg-muted/30"
      )}
    >
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <CardTitle
                className={cn(
                  "text-base leading-snug",
                  isRead && "text-muted-foreground"
                )}
              >
                <HighlightTitle text={paper.title} keywords={highlightKeywords} />
              </CardTitle>
              {paper.is_new && (
                <Badge className="shrink-0 gap-1 bg-purple-600 text-white hover:bg-purple-600">
                  <BellRing className="size-3" />
                  新推送
                </Badge>
              )}
            </div>
            <CardDescription>
              {authorsStr} · {paper.source} · {dateStr}
            </CardDescription>
          </div>
          {isRead && (
            <Badge variant="secondary" className="shrink-0 gap-1">
              <CheckCircle2 className="size-3" />
              已读
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* AI Summary */}
        {paper.ai_summary && (
          <div
            className={cn(
              "rounded-lg p-4",
              isRead ? "bg-muted" : "bg-purple-50"
            )}
          >
            <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-purple-700">
              <Sparkles className="size-4" />
              AI 摘要
            </div>
            <p className="text-sm leading-relaxed text-foreground/80">
              {paper.ai_summary}
            </p>
          </div>
        )}

        {/* Problem solved */}
        {paper.ai_problem_solved && (
          <div>
            <p className="mb-1 text-xs font-medium text-muted-foreground">
              能解决什么问题
            </p>
            <p className="text-sm text-foreground/80">
              {paper.ai_problem_solved}
            </p>
          </div>
        )}

        {/* Abstract fallback */}
        {!paper.ai_summary && paper.abstract && (
          <div>
            <p className="mb-1 text-xs font-medium text-muted-foreground">摘要</p>
            <p className="text-sm text-foreground/80 line-clamp-3">
              {paper.abstract}
            </p>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-2 border-t pt-3">
          {paper.url && (
            <a href={paper.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
              <Button variant="default" size="sm" className="gap-1">
                <ExternalLink className="size-3.5" />
                原文
              </Button>
            </a>
          )}
          <Button
            variant={isBookmarked ? "secondary" : "outline"}
            size="sm"
            className="gap-1"
            onClick={handleBookmark}
          >
            {isBookmarked ? (
              <BookmarkCheck className="size-3.5" />
            ) : (
              <Bookmark className="size-3.5" />
            )}
            收藏
          </Button>
          <Button
            variant={isRead ? "secondary" : "ghost"}
            size="sm"
            className="gap-1"
            onClick={handleMarkRead}
          >
            <CheckCircle2 className="size-3.5" />
            {isRead ? "已读" : "标记已读"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
