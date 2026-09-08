"use client";

import { Keyboard } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";

interface KeyboardHelpProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface ShortcutItem {
  keys: string[];
  description: string;
}

interface ShortcutGroup {
  title: string;
  shortcuts: ShortcutItem[];
}

const shortcutGroups: ShortcutGroup[] = [
  {
    title: "全局快捷键",
    shortcuts: [
      { keys: ["⌘", "K"], description: "打开全局搜索" },
      { keys: ["⌘", "N"], description: "添加新研究主题" },
      { keys: ["⌘", "Shift", "N"], description: "新建对话" },
      { keys: [","], description: "打开设置" },
      { keys: ["?"], description: "显示快捷键帮助" },
      { keys: ["⌘", "/"], description: "显示/隐藏侧边栏" },
    ],
  },
  {
    title: "列表快捷键",
    shortcuts: [
      { keys: ["↑"], description: "上一篇论文" },
      { keys: ["↓"], description: "下一篇论文" },
      { keys: ["Enter"], description: "打开论文详情" },
      { keys: ["S"], description: "收藏/取消收藏" },
      { keys: ["E"], description: "打开导出面板" },
      { keys: ["⌘", "A"], description: "全选论文" },
      { keys: ["Del"], description: "删除选中项" },
    ],
  },
  {
    title: "对话快捷键",
    shortcuts: [
      { keys: ["Enter"], description: "发送消息" },
      { keys: ["Shift", "Enter"], description: "换行" },
      { keys: ["⌘", "Shift", "C"], description: "复制对话内容" },
      { keys: ["⌘", "Shift", "D"], description: "清空对话" },
      { keys: ["↑"], description: "上一条历史消息" },
      { keys: ["Esc"], description: "关闭对话面板" },
    ],
  },
];

function KbdGroup({ keys }: { keys: string[] }) {
  return (
    <span className="inline-flex items-center gap-0.5">
      {keys.map((key, i) => (
        <span key={i}>
          <kbd className="inline-flex items-center justify-center h-5 min-w-[20px] px-1.5 rounded border bg-muted font-mono text-[10px] font-medium text-muted-foreground shadow-[0_1px_0_1px_rgba(0,0,0,0.1)]">
            {key}
          </kbd>
          {i < keys.length - 1 && (
            <span className="text-muted-foreground/50 mx-0.5">+</span>
          )}
        </span>
      ))}
    </span>
  );
}

export function KeyboardHelp({ open, onOpenChange }: KeyboardHelpProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Keyboard className="size-4" />
            快捷键
          </DialogTitle>
          <DialogDescription>
            使用键盘快捷键可以更高效地操作 Paper Finder。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          {shortcutGroups.map((group, gi) => (
            <div key={gi}>
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                {group.title}
              </h3>
              <div className="rounded-lg border divide-y">
                {group.shortcuts.map((shortcut, si) => (
                  <div
                    key={si}
                    className="flex items-center justify-between px-3 py-2"
                  >
                    <span className="text-sm">{shortcut.description}</span>
                    <KbdGroup keys={shortcut.keys} />
                  </div>
                ))}
              </div>
              {gi < shortcutGroups.length - 1 && <Separator className="mt-4" />}
            </div>
          ))}
        </div>

        <div className="text-center pt-2">
          <p className="text-xs text-muted-foreground">
            按{" "}
            <kbd className="inline-flex items-center justify-center h-4 min-w-[16px] px-1 rounded border bg-muted font-mono text-[9px] font-medium text-muted-foreground">
              ?
            </kbd>{" "}
            随时打开此面板
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
