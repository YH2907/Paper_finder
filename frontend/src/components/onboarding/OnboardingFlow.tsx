"use client";

import { useState } from "react";
import {
  BookOpen,
  Tags,
  Bell,
  ChevronRight,
  ChevronLeft,
  Check,
  Sparkles,
  Plus,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

interface OnboardingStep {
  title: string;
  description: string;
  icon: React.ReactNode;
}

const steps: OnboardingStep[] = [
  {
    title: "添加研究主题",
    description: "告诉我们您关注的研究方向，我们将为您筛选相关论文",
    icon: <BookOpen className="size-6" />,
  },
  {
    title: "添加关键词",
    description: "设置关键词以便更精准地匹配您感兴趣的论文",
    icon: <Tags className="size-6" />,
  },
  {
    title: "设置推送偏好",
    description: "选择您希望接收论文更新的方式和频率",
    icon: <Bell className="size-6" />,
  },
];

export function OnboardingFlow({ onComplete }: { onComplete?: () => void }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [topics, setTopics] = useState<string[]>(["自然语言处理"]);
  const [topicInput, setTopicInput] = useState("");
  const [keywords, setKeywords] = useState<string[]>(["Transformer", "GPT"]);
  const [keywordInput, setKeywordInput] = useState("");
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [dailyDigest, setDailyDigest] = useState(false);
  const [weeklyReport, setWeeklyReport] = useState(true);

  const addItem = (
    value: string,
    list: string[],
    setList: (v: string[]) => void,
    setInput: (v: string) => void
  ) => {
    const trimmed = value.trim();
    if (trimmed && !list.includes(trimmed)) {
      setList([...list, trimmed]);
      setInput("");
    }
  };

  const removeItem = (
    item: string,
    list: string[],
    setList: (v: string[]) => void
  ) => {
    setList(list.filter((i) => i !== item));
  };

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onComplete?.();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const isLastStep = currentStep === steps.length - 1;

  return (
    <div className="flex flex-col items-center justify-center min-h-[500px] max-w-lg mx-auto p-6">
      {/* 进度指示 */}
      <div className="flex items-center gap-2 mb-8">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center">
            <div
              className={cn(
                "size-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors",
                i < currentStep
                  ? "bg-primary text-primary-foreground"
                  : i === currentStep
                    ? "bg-primary text-primary-foreground ring-4 ring-primary/20"
                    : "bg-muted text-muted-foreground"
              )}
            >
              {i < currentStep ? (
                <Check className="size-4" />
              ) : (
                i + 1
              )}
            </div>
            {i < steps.length - 1 && (
              <div
                className={cn(
                  "w-12 h-0.5 mx-1",
                  i < currentStep ? "bg-primary" : "bg-muted"
                )}
              />
            )}
          </div>
        ))}
      </div>

      {/* 步骤内容 */}
      <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center size-12 rounded-full bg-primary/10 text-primary mb-4">
          {steps[currentStep].icon}
        </div>
        <h2 className="text-xl font-semibold mb-2">
          {steps[currentStep].title}
        </h2>
        <p className="text-sm text-muted-foreground">
          {steps[currentStep].description}
        </p>
      </div>

      {/* 步骤 1：添加研究主题 */}
      {currentStep === 0 && (
        <div className="w-full space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="输入研究主题，如：机器学习"
              value={topicInput}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setTopicInput(e.target.value)
              }
              onKeyDown={(e: React.KeyboardEvent) =>
                e.key === "Enter" &&
                addItem(topicInput, topics, setTopics, setTopicInput)
              }
              className="flex-1"
            />
            <Button
              variant="outline"
              size="icon"
              onClick={() =>
                addItem(topicInput, topics, setTopics, setTopicInput)
              }
            >
              <Plus className="size-4" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {topics.map((topic) => (
              <Badge
                key={topic}
                variant="secondary"
                className="gap-1 pr-1 text-sm py-1"
              >
                {topic}
                <button
                  onClick={() => removeItem(topic, topics, setTopics)}
                  className="ml-1 hover:bg-muted rounded-full p-0.5"
                >
                  <X className="size-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-xs text-muted-foreground mb-2">推荐主题：</p>
            <div className="flex flex-wrap gap-1.5">
              {["计算机视觉", "强化学习", "知识图谱", "推荐系统"].map(
                (suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() =>
                      addItem(
                        suggestion,
                        topics,
                        setTopics,
                        setTopicInput
                      )
                    }
                    className="text-xs px-2.5 py-1 rounded-full bg-background hover:bg-muted border transition-colors"
                  >
                    + {suggestion}
                  </button>
                )
              )}
            </div>
          </div>
        </div>
      )}

      {/* 步骤 2：添加关键词 */}
      {currentStep === 1 && (
        <div className="w-full space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="输入关键词，如：LLM"
              value={keywordInput}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setKeywordInput(e.target.value)
              }
              onKeyDown={(e: React.KeyboardEvent) =>
                e.key === "Enter" &&
                addItem(
                  keywordInput,
                  keywords,
                  setKeywords,
                  setKeywordInput
                )
              }
              className="flex-1"
            />
            <Button
              variant="outline"
              size="icon"
              onClick={() =>
                addItem(keywordInput, keywords, setKeywords, setKeywordInput)
              }
            >
              <Plus className="size-4" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {keywords.map((kw) => (
              <Badge
                key={kw}
                variant="secondary"
                className="gap-1 pr-1 text-sm py-1"
              >
                {kw}
                <button
                  onClick={() => removeItem(kw, keywords, setKeywords)}
                  className="ml-1 hover:bg-muted rounded-full p-0.5"
                >
                  <X className="size-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-xs text-muted-foreground mb-2">推荐关键词：</p>
            <div className="flex flex-wrap gap-1.5">
              {["RAG", "Fine-tuning", "RLHF", "多模态", "Agent", "向量数据库"].map(
                (suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() =>
                      addItem(
                        suggestion,
                        keywords,
                        setKeywords,
                        setKeywordInput
                      )
                    }
                    className="text-xs px-2.5 py-1 rounded-full bg-background hover:bg-muted border transition-colors"
                  >
                    + {suggestion}
                  </button>
                )
              )}
            </div>
          </div>
        </div>
      )}

      {/* 步骤 3：设置推送偏好 */}
      {currentStep === 2 && (
        <div className="w-full space-y-4">
          <div className="space-y-3 bg-muted/30 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">邮件通知</p>
                <p className="text-xs text-muted-foreground">
                  有新论文时发送邮件提醒
                </p>
              </div>
              <Switch
                checked={emailEnabled}
                onCheckedChange={setEmailEnabled}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">每日摘要</p>
                <p className="text-xs text-muted-foreground">
                  每天早上发送当日论文摘要
                </p>
              </div>
              <Switch
                checked={dailyDigest}
                onCheckedChange={setDailyDigest}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">每周报告</p>
                <p className="text-xs text-muted-foreground">
                  每周发送论文趋势分析报告
                </p>
              </div>
              <Switch
                checked={weeklyReport}
                onCheckedChange={setWeeklyReport}
              />
            </div>
          </div>
        </div>
      )}

      {/* 导航按钮 */}
      <div className="flex items-center gap-3 mt-8 w-full">
        {currentStep > 0 && (
          <Button variant="outline" onClick={handlePrev} className="gap-1">
            <ChevronLeft className="size-4" />
            上一步
          </Button>
        )}
        <div className="flex-1" />
        <Button onClick={handleNext} className="gap-1">
          {isLastStep ? (
            <>
              <Sparkles className="size-4" />
              完成设置
            </>
          ) : (
            <>
              下一步
              <ChevronRight className="size-4" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
