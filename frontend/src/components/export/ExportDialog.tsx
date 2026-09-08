"use client";

import { useState } from "react";
import {
  Download,
  FileText,
  FolderOpen,
  MessageSquare,
  FileSpreadsheet,
  FileJson,
  FileDown,
  Check,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type ExportContent = "papers" | "topics" | "conversations";
type ExportFormat = "csv" | "json" | "markdown";

const contentOptions: {
  value: ExportContent;
  label: string;
  description: string;
  icon: React.ReactNode;
  count: number;
}[] = [
  {
    value: "papers",
    label: "收藏论文",
    description: "导出您收藏的所有论文及元数据",
    icon: <FileText className="size-4 text-blue-500" />,
    count: 24,
  },
  {
    value: "topics",
    label: "主题配置",
    description: "导出研究主题和关键词设置",
    icon: <FolderOpen className="size-4 text-green-500" />,
    count: 5,
  },
  {
    value: "conversations",
    label: "对话历史",
    description: "导出与 AI 的论文讨论记录",
    icon: <MessageSquare className="size-4 text-purple-500" />,
    count: 18,
  },
];

const formatOptions: {
  value: ExportFormat;
  label: string;
  description: string;
  icon: React.ReactNode;
}[] = [
  {
    value: "csv",
    label: "CSV",
    description: "适合在 Excel 中查看和分析",
    icon: <FileSpreadsheet className="size-5 text-green-600" />,
  },
  {
    value: "json",
    label: "JSON",
    description: "适合程序处理和数据迁移",
    icon: <FileJson className="size-5 text-orange-500" />,
  },
  {
    value: "markdown",
    label: "Markdown",
    description: "适合文档阅读和笔记整理",
    icon: <FileDown className="size-5 text-blue-500" />,
  },
];

export function ExportDialog({ open, onOpenChange }: ExportDialogProps) {
  const [selectedContents, setSelectedContents] = useState<ExportContent[]>([
    "papers",
  ]);
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>("csv");
  const [exporting, setExporting] = useState(false);

  const toggleContent = (value: ExportContent) => {
    setSelectedContents((prev) =>
      prev.includes(value)
        ? prev.filter((v) => v !== value)
        : [...prev, value]
    );
  };

  const handleExport = () => {
    setExporting(true);
    // 模拟导出过程
    setTimeout(() => {
      setExporting(false);
      onOpenChange(false);
    }, 2000);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="size-4" />
            导出数据
          </DialogTitle>
          <DialogDescription>
            选择要导出的内容和格式，导出文件将自动下载到您的设备。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          {/* 选择导出内容 */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">
              导出内容
            </p>
            <div className="space-y-2">
              {contentOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => toggleContent(option.value)}
                  className={cn(
                    "flex items-center gap-3 w-full p-3 rounded-lg border transition-all text-left",
                    selectedContents.includes(option.value)
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-muted/50"
                  )}
                >
                  <div
                    className={cn(
                      "size-5 rounded-md border flex items-center justify-center transition-colors",
                      selectedContents.includes(option.value)
                        ? "bg-primary border-primary"
                        : "border-muted-foreground/30"
                    )}
                  >
                    {selectedContents.includes(option.value) && (
                      <Check className="size-3 text-primary-foreground" />
                    )}
                  </div>
                  {option.icon}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">
                        {option.label}
                      </span>
                      <Badge variant="secondary" className="text-[10px]">
                        {option.count} 项
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {option.description}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* 选择导出格式 */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">
              导出格式
            </p>
            <div className="grid grid-cols-3 gap-2">
              {formatOptions.map((format) => (
                <button
                  key={format.value}
                  onClick={() => setSelectedFormat(format.value)}
                  className={cn(
                    "flex flex-col items-center gap-2 p-3 rounded-lg border transition-all text-center",
                    selectedFormat === format.value
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-muted/50"
                  )}
                >
                  {format.icon}
                  <span className="text-sm font-medium">{format.label}</span>
                  <span className="text-[10px] text-muted-foreground leading-tight">
                    {format.description}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={exporting}
          >
            取消
          </Button>
          <Button
            onClick={handleExport}
            disabled={selectedContents.length === 0 || exporting}
            className="gap-1.5"
          >
            {exporting ? (
              <>
                <span className="size-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                导出中...
              </>
            ) : (
              <>
                <Download className="size-4" />
                导出{" "}
                {selectedContents.length > 0 &&
                  `(${selectedContents.length} 项)`}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
