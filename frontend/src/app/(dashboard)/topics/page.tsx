"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Plus,
  Pencil,
  Pause,
  Trash2,
  Tag,
  TrendingUp,
  Loader2,
  Brain,
  FileText,
  CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";
import {
  getTopics,
  createTopic,
  updateTopic,
  deleteTopic,
  type Topic,
} from "@/lib/api";

export default function TopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTopic, setEditingTopic] = useState<Topic | null>(null);
  const [formName, setFormName] = useState("");
  const [formKeywords, setFormKeywords] = useState("");
  const [formExclude, setFormExclude] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formProblemStatement, setFormProblemStatement] = useState("");
  const [saving, setSaving] = useState(false);
  const [formErrors, setFormErrors] = useState<{ name?: string; keywords?: string }>({});

  // 加载主题列表
  useEffect(() => {
    loadTopics();
  }, []);

  async function loadTopics() {
    setLoading(true);
    try {
      const res = await getTopics();
      if (res.success) {
        setTopics(res.data);
      }
    } catch {
      setError("加载主题失败");
    } finally {
      setLoading(false);
    }
  }

  const handleOpenNew = () => {
    setEditingTopic(null);
    setFormName("");
    setFormKeywords("");
    setFormExclude("");
    setFormDescription("");
    setFormProblemStatement("");
    setFormErrors({});
    setDialogOpen(true);
  };

  const handleOpenEdit = (topic: Topic) => {
    setEditingTopic(topic);
    setFormName(topic.name);
    setFormKeywords(topic.keywords.join(", "));
    setFormExclude(topic.exclude_keywords.join(", "));
    setFormDescription(topic.description || "");
    setFormProblemStatement(topic.problem_statement || "");
    setFormErrors({});
    setDialogOpen(true);
  };

  const validateForm = () => {
    const errors: { name?: string; keywords?: string } = {};
    if (!formName.trim()) {
      errors.name = "请输入主题名称";
    }
    if (!formKeywords.trim()) {
      errors.keywords = "请输入至少一个关键词";
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSave = async () => {
    if (!validateForm()) return;
    setSaving(true);
    setError("");

    const keywords = formKeywords
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean);
    const excludeKeywords = formExclude
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean);

    try {
      if (editingTopic) {
        await updateTopic(editingTopic.id, {
          name: formName,
          keywords,
          exclude_keywords: excludeKeywords,
          description: formDescription || undefined,
          problem_statement: formProblemStatement || undefined,
        });
        toast.success("主题已更新", {
          description: `「${formName}」修改成功`,
        });
      } else {
        await createTopic({
          name: formName,
          keywords,
          exclude_keywords: excludeKeywords,
          description: formDescription || undefined,
          problem_statement: formProblemStatement || undefined,
        });
        toast.success("主题已创建", {
          description: `「${formName}」已添加到研究主题列表`,
        });
      }
      setDialogOpen(false);
      loadTopics();
    } catch {
      toast.error("保存失败", {
        description: "请检查网络连接后重试",
      });
      setError("保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (topic: Topic) => {
    try {
      await updateTopic(topic.id, { is_active: !topic.is_active });
      toast.success(
        topic.is_active ? "主题已暂停" : "主题已启用",
        { description: `「${topic.name}」${topic.is_active ? "已暂停" : "已启用"}` }
      );
      loadTopics();
    } catch {
      toast.error("操作失败");
      setError("操作失败");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这个主题吗？")) return;
    try {
      await deleteTopic(id);
      toast.success("主题已删除");
      loadTopics();
    } catch {
      toast.error("删除失败");
      setError("删除失败");
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
          <h1 className="text-2xl font-bold">研究主题管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            管理你的研究兴趣主题，定义你想要解决的问题，系统将自动搜索并推送相关论文
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger render={<Button />} onClick={handleOpenNew}>
            <Plus className="size-4" />
            添加新主题
          </DialogTrigger>
          <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingTopic ? "编辑主题" : "添加新主题"}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-5">
              {/* Basic info section */}
              <div className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-sm font-medium">
                    主题名称 <span className="text-red-500">*</span>
                  </label>
                  <Input
                    placeholder="例如：大语言模型、多模态学习"
                    value={formName}
                    onChange={(e) => {
                      setFormName(e.target.value);
                      if (formErrors.name) setFormErrors((p) => ({ ...p, name: undefined }));
                    }}
                  />
                  {formErrors.name && (
                    <p className="mt-1 text-xs text-red-500">{formErrors.name}</p>
                  )}
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium">
                    关键词 <span className="text-red-500">*</span>
                  </label>
                  <Input
                    placeholder="用逗号分隔，例如：LLM, GPT, Transformer"
                    value={formKeywords}
                    onChange={(e) => {
                      setFormKeywords(e.target.value);
                      if (formErrors.keywords) setFormErrors((p) => ({ ...p, keywords: undefined }));
                    }}
                  />
                  {formErrors.keywords && (
                    <p className="mt-1 text-xs text-red-500">{formErrors.keywords}</p>
                  )}
                  {!formErrors.keywords && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      多个关键词用英文逗号分隔，用于基础论文搜索
                    </p>
                  )}
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium">
                    排除词
                  </label>
                  <Input
                    placeholder="用逗号分隔，例如：综述, survey"
                    value={formExclude}
                    onChange={(e) => setFormExclude(e.target.value)}
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    包含排除词的论文将被过滤
                  </p>
                </div>
              </div>

              {/* Divider */}
              <div className="border-t pt-5">
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="size-4 text-primary" />
                  <label className="text-sm font-medium">
                    问题驱动搜索（可选）
                  </label>
                </div>
                <p className="text-xs text-muted-foreground mb-4">
                  定义你想要解决的具体问题，AI 将根据问题分析生成更精准的搜索关键词
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="mb-1.5 block text-sm font-medium">
                      主题描述
                    </label>
                    <Textarea
                      placeholder="简要描述研究背景和方向，例如：研究如何提高大语言模型在复杂推理任务中的表现..."
                      value={formDescription}
                      onChange={(e) => setFormDescription(e.target.value)}
                      rows={2}
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium">
                      问题陈述
                    </label>
                    <Textarea
                      placeholder="描述你想要解决的具体问题，例如：如何让 LLM 在数学推理、代码生成等复杂任务上表现更好？有哪些新的方法和技术？..."
                      value={formProblemStatement}
                      onChange={(e) => setFormProblemStatement(e.target.value)}
                      rows={3}
                    />
                    <p className="mt-1 text-xs text-muted-foreground">
                      详细描述问题将帮助 AI 生成更精准的搜索关键词
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                取消
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    保存中...
                  </>
                ) : editingTopic ? (
                  <>
                    <CheckCircle2 className="size-4" />
                    保存修改
                  </>
                ) : (
                  <>
                    <Plus className="size-4" />
                    创建主题
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {topics.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <div className="mb-3">
              <Tag className="mx-auto size-10 text-muted-foreground/50" />
            </div>
            <p className="text-lg font-medium">还没有研究主题</p>
            <p className="mt-1 text-sm">点击上方按钮创建第一个研究主题</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {topics.map((topic) => (
            <Card key={topic.id} className="transition-shadow hover:shadow-md">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="flex items-center gap-2">
                      <Tag className="size-4 text-primary" />
                      {topic.name}
                      {!topic.is_active && (
                        <Badge variant="secondary">已暂停</Badge>
                      )}
                    </CardTitle>
                    <CardDescription className="mt-2">
                      <div className="flex flex-wrap gap-1.5">
                        {topic.keywords.map((kw, idx) => (
                          <Badge key={`${kw}-${idx}`} variant="outline">
                            {kw}
                          </Badge>
                        ))}
                      </div>
                      {topic.exclude_keywords.length > 0 && (
                        <div className="mt-2 flex items-center gap-1.5 text-xs">
                          <span className="text-muted-foreground">
                            排除词：
                          </span>
                          {topic.exclude_keywords.map((ew) => (
                            <Badge
                              key={ew}
                              variant="destructive"
                              className="text-xs"
                            >
                              {ew}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {/* 显示问题陈述 */}
                {(topic.description || topic.problem_statement) && (
                  <div className="mb-4 rounded-lg bg-muted/50 p-3">
                    {topic.description && (
                      <div className="flex items-start gap-2 mb-2">
                        <FileText className="size-3.5 mt-0.5 text-muted-foreground" />
                        <p className="text-xs text-muted-foreground">
                          {topic.description}
                        </p>
                      </div>
                    )}
                    {topic.problem_statement && (
                      <div className="flex items-start gap-2">
                        <Brain className="size-3.5 mt-0.5 text-primary" />
                        <p className="text-xs text-foreground">
                          {topic.problem_statement}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1.5">
                    <TrendingUp className="size-4 text-green-600" />
                    <span>
                      创建于{" "}
                      {new Date(topic.created_at).toLocaleDateString("zh-CN")}
                    </span>
                  </div>
                </div>
                <div className="mt-4 flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenEdit(topic)}
                  >
                    <Pencil className="size-3.5" />
                    编辑
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleToggle(topic)}
                  >
                    <Pause className="size-3.5" />
                    {topic.is_active ? "暂停" : "启用"}
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDelete(topic.id)}
                  >
                    <Trash2 className="size-3.5" />
                    删除
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
