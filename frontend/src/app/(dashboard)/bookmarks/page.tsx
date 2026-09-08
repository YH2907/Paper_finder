"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Bookmark,
  ExternalLink,
  Trash2,
  Calendar,
  Users,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import {
  getBookmarkedPapers,
  unbookmarkPaper,
  type Paper,
} from "@/lib/api";

export default function BookmarksPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadBookmarks = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getBookmarkedPapers(1, 100);
      if (res.success) {
        setPapers(res.data.papers);
        setTotal(res.data.total);
      }
    } catch {
      setError("加载收藏失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBookmarks();
  }, [loadBookmarks]);

  // 页面获得焦点时重新加载
  useEffect(() => {
    const handleFocus = () => {
      loadBookmarks();
    };
    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, [loadBookmarks]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadBookmarks();
    setRefreshing(false);
  };

  const handleRemove = async (paperId: string, paperTitle: string) => {
    if (!confirm("确定要取消收藏吗？")) return;
    try {
      await unbookmarkPaper(paperId);
      setPapers((prev) => prev.filter((p) => p.id !== paperId));
      setTotal((prev) => prev - 1);
      toast.success("已取消收藏", {
        description: `「${paperTitle}」已从收藏夹移除`,
      });
    } catch {
      toast.error("取消收藏失败");
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center p-6">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <Bookmark className="size-6 text-primary" />
            我的收藏
            <span className="text-base font-normal text-muted-foreground">
              ({total}篇)
            </span>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            你收藏的论文将保存在这里，方便随时查阅
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

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="space-y-4">
        {papers.map((paper) => (
          <Card
            key={paper.id}
            className="transition-shadow hover:shadow-md cursor-pointer"
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <Link href={`/papers/${paper.id}`} className="flex-1">
                  <CardTitle className="text-base leading-relaxed hover:text-primary transition-colors">
                    {paper.title}
                  </CardTitle>
                </Link>
              </div>
              <CardDescription className="mt-2">
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <span className="flex items-center gap-1">
                    <Users className="size-3.5" />
                    {paper.authors?.join(", ") || "未知作者"}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="size-3.5" />
                    {paper.source} ·{" "}
                    {paper.published_at
                      ? new Date(paper.published_at).toLocaleDateString("zh-CN")
                      : "未知日期"}
                  </span>
                </div>
              </CardDescription>
            </CardHeader>
            <CardContent>
              {paper.ai_summary ? (
                <p className="text-sm text-muted-foreground">{paper.ai_summary}</p>
              ) : paper.abstract ? (
                <p className="text-sm text-muted-foreground line-clamp-3">
                  {paper.abstract}
                </p>
              ) : null}
              <div className="mt-4 flex items-center justify-end gap-2">
                {paper.url && (
                  <a href={paper.url} target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" size="sm">
                      <ExternalLink className="size-3.5" />
                      查看原文
                    </Button>
                  </a>
                )}
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleRemove(paper.id, paper.title)}
                >
                  <Trash2 className="size-3.5" />
                  取消收藏
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {papers.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
          <Bookmark className="mb-4 size-12" />
          <p className="text-lg font-medium">暂无收藏</p>
          <p className="mt-1 text-sm">浏览论文时点击收藏按钮即可添加</p>
        </div>
      )}
    </div>
  );
}
