"use client";

import { useState } from "react";
import { Search, Loader2, AlertCircle, Sparkles, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { deepResearch, type DeepResearchResult, type SimplePaper } from "@/lib/api";
import { toast } from "sonner";

interface DeepResearchModalProps {
  topicId?: string;
  onClose: () => void;
  onSelectPaper?: (paper: SimplePaper) => void;
}

export default function DeepResearchModal({
  topicId,
  onClose,
  onSelectPaper,
}: DeepResearchModalProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DeepResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) {
      toast.error("请输入研究问题");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await deepResearch(query.trim(), topicId, 20);
      if (res.success && res.data) {
        setResult(res.data);
        toast.success(`找到 ${res.data.total} 篇相关论文`);
      } else {
        setError(res.message || "深度研究失败");
        toast.error(res.message || "深度研究失败");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "发生错误";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end bg-black/50 sm:items-center sm:justify-center">
      <Card className="w-full sm:max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <CardHeader className="border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="size-5 text-purple-600" />
              <CardTitle>深度研究</CardTitle>
            </div>
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground"
            >
              ✕
            </button>
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            AI 智能分析问题，搜索并排序相关论文，按解决问题程度优先
          </p>
        </CardHeader>

        {/* Content */}
        <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Search Input */}
          <div className="space-y-2">
            <label className="text-sm font-medium">研究问题</label>
            <div className="flex gap-2">
              <Input
                placeholder="描述你的研究问题或想法..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) =>
                  e.key === "Enter" && !loading && handleSearch()
                }
                disabled={loading}
                className="flex-1"
              />
              <Button
                onClick={handleSearch}
                disabled={loading || !query.trim()}
                className="gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    研究中...
                  </>
                ) : (
                  <>
                    <Search className="size-4" />
                    分析
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Error State */}
          {error && (
            <div className="flex gap-3 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">
              <AlertCircle className="size-4 shrink-0 mt-0.5" />
              <div>{error}</div>
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-4">
              {/* Analysis */}
              <div className="space-y-3">
                <h3 className="font-semibold text-sm">问题分析</h3>
                <div className="rounded-lg bg-muted p-3 space-y-2">
                  {result.analysis.main_concepts && result.analysis.main_concepts.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">
                        关键概念
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {result.analysis.main_concepts.map((concept, i) => (
                          <Badge key={i} variant="secondary" className="text-xs">
                            {concept}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {result.analysis.research_objectives && result.analysis.research_objectives.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">
                        研究目标
                      </p>
                      <ul className="text-xs space-y-1">
                        {result.analysis.research_objectives.map((obj, i) => (
                          <li key={i} className="text-foreground">
                            • {obj}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {result.analysis.search_keywords && result.analysis.search_keywords.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">
                        搜索关键词
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {result.analysis.search_keywords.map((kw, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {kw}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Papers */}
              <div className="space-y-3">
                <h3 className="font-semibold text-sm">
                  相关论文 ({result.total} 篇)
                </h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {result.papers && result.papers.length > 0 ? (
                    result.papers.map((paper, i) => (
                      <button
                        key={paper.id}
                        onClick={() => onSelectPaper?.(paper)}
                        className="w-full text-left"
                      >
                        <div
                          className={cn(
                            "group rounded-lg border bg-card p-3 transition-all hover:shadow-md hover:border-purple-300",
                            "dark:hover:border-purple-700"
                          )}
                        >
                          <div className="flex items-start gap-3">
                            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/50 mt-0.5">
                              <span className="text-xs font-bold text-purple-600">
                                {i + 1}
                              </span>
                            </div>

                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-sm line-clamp-2 text-foreground">
                                {paper.title}
                              </p>
                              {paper.authors && paper.authors.length > 0 && (
                                <p className="text-xs text-muted-foreground line-clamp-1 mt-1">
                                  {paper.authors.slice(0, 3).join(", ")}
                                  {paper.authors.length > 3 ? "..." : ""}
                                </p>
                              )}
                              {paper.abstract && (
                                <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                                  {paper.abstract}
                                </p>
                              )}
                              <p className="text-xs text-muted-foreground mt-2">
                                {paper.source}
                                {paper.published_at &&
                                  ` · ${new Date(
                                    paper.published_at
                                  ).toLocaleDateString("zh-CN")}`}
                              </p>
                            </div>

                            <FileText className="size-4 text-muted-foreground group-hover:text-purple-600 dark:group-hover:text-purple-400 shrink-0 mt-1" />
                          </div>
                        </div>
                      </button>
                    ))
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <p className="text-sm">未找到相关论文</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!result && !error && !loading && (
            <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
              <Sparkles className="size-12 opacity-20" />
              <div className="space-y-2">
                <p className="text-sm font-medium text-foreground">
                  开始深度研究
                </p>
                <p className="text-xs text-muted-foreground max-w-sm">
                  输入你的研究问题，AI 将为你深度分析问题、搜索相关论文，并按**能解决最多问题的优先级**排序
                </p>
              </div>
              
              {/* Example Queries */}
              <div className="pt-4 space-y-2">
                <p className="text-xs font-medium text-muted-foreground">示例问题：</p>
                <div className="space-y-1">
                  <button
                    onClick={() => setQuery("如何改进深度学习模型的泛化能力？")}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    • 如何改进深度学习模型的泛化能力？
                  </button>
                  <button
                    onClick={() => setQuery("自然语言处理中的注意力机制有哪些应用？")}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    • 自然语言处理中的注意力机制有哪些应用？
                  </button>
                  <button
                    onClick={() => setQuery("时间序列预测有哪些有效的方法？")}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    • 时间序列预测有哪些有效的方法？
                  </button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
