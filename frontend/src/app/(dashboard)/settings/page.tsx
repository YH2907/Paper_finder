"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Settings,
  User,
  Shield,
  Keyboard,
  Download,
  Save,
  LogOut,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import {
  getMe,
  updateUser,
  removeToken,
  type User as UserType,
} from "@/lib/api";

export default function SettingsPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [user, setUser] = useState<UserType | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("profile");

  // Profile form state
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    async function loadUser() {
      try {
        const res = await getMe();
        if (res.success) {
          setUser(res.data);
          setName(res.data.name || "");
        }
      } catch {
        // 未登录
      } finally {
        setLoading(false);
      }
    }
    loadUser();
  }, []);

  const handleLogout = () => {
    removeToken();
    router.push("/login");
  };

  const handleSaveProfile = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setSaved(false);
    try {
      const res = await updateUser({ name: name.trim() });
      if (res.success) {
        setUser(res.data);
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      }
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const tabs = [
    { id: "profile", label: "个人信息", icon: User },
    { id: "security", label: "账号安全", icon: Shield },
    { id: "shortcuts", label: "快捷键", icon: Keyboard },
    { id: "export", label: "导出数据", icon: Download },
  ];

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center p-6">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Settings className="size-6 text-primary" />
          设置
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          管理你的账户设置和偏好
        </p>
      </div>

      {/* Tab 菜单 */}
      <div className="mb-6 flex gap-2 border-b border-border pb-2 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <Icon className="size-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab 内容 */}
      {activeTab === "profile" && (
        <Card>
          <CardHeader>
            <CardTitle>个人信息</CardTitle>
            <CardDescription>管理你的个人资料信息</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm font-medium">
                  用户名
                </label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="请输入用户名"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">
                  邮箱
                </label>
                <Input
                  defaultValue={user?.email || ""}
                  type="email"
                  disabled
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">
                  注册时间
                </label>
                <Input
                  defaultValue={
                    user?.created_at
                      ? new Date(user.created_at).toLocaleDateString("zh-CN")
                      : ""
                  }
                  disabled
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={handleSaveProfile} disabled={saving || !name.trim()}>
                {saving ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : saved ? (
                  <CheckCircle2 className="size-4" />
                ) : (
                  <Save className="size-4" />
                )}
                {saved ? "已保存" : saving ? "保存中..." : "保存修改"}
              </Button>
              {saved && (
                <span className="text-sm text-green-600">保存成功！</span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === "security" && (
        <Card>
          <CardHeader>
            <CardTitle>账号安全</CardTitle>
            <CardDescription>管理你的账号安全设置</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium">修改密码</span>
                <p className="text-xs text-muted-foreground">
                  定期修改密码以保障账号安全
                </p>
              </div>
              <Button variant="outline" size="sm">
                修改密码
              </Button>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium">两步验证</span>
                <p className="text-xs text-muted-foreground">
                  启用两步验证增强账号安全性
                </p>
              </div>
              <Switch />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium">登录历史</span>
                <p className="text-xs text-muted-foreground">
                  查看最近的登录活动
                </p>
              </div>
              <Button variant="outline" size="sm">
                查看历史
              </Button>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium">退出登录</span>
                <p className="text-xs text-muted-foreground">
                  退出当前账号
                </p>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleLogout}
              >
                <LogOut className="size-3.5" />
                退出登录
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === "shortcuts" && (
        <Card>
          <CardHeader>
            <CardTitle>快捷键</CardTitle>
            <CardDescription>使用快捷键提升操作效率</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { keys: ["⌘", "K"], description: "打开搜索" },
                { keys: ["⌘", "N"], description: "新建研究主题" },
                { keys: ["⌘", "B"], description: "收藏当前论文" },
                { keys: ["⌘", "Enter"], description: "发送消息" },
                { keys: ["⌘", "Shift", "P"], description: "打开命令面板" },
                { keys: ["⌘", ","], description: "打开设置" },
                { keys: ["⌘", "Shift", "E"], description: "导出数据" },
                { keys: ["Esc"], description: "关闭弹窗 / 返回" },
                { keys: ["?"], description: "显示快捷键帮助" },
              ].map((shortcut, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between rounded-lg border border-border px-4 py-2.5"
                >
                  <span className="text-sm">{shortcut.description}</span>
                  <div className="flex gap-1">
                    {shortcut.keys.map((key, i) => (
                      <kbd
                        key={i}
                        className="inline-flex h-6 min-w-6 items-center justify-center rounded border border-border bg-muted px-1.5 text-xs font-medium text-muted-foreground"
                      >
                        {key}
                      </kbd>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === "export" && (
        <Card>
          <CardHeader>
            <CardTitle>导出数据</CardTitle>
            <CardDescription>导出你的研究数据和收藏</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              {
                title: "收藏论文列表",
                description: "导出所有收藏的论文信息（标题、作者、摘要等）",
                format: "CSV / JSON / BibTeX",
              },
              {
                title: "研究主题配置",
                description: "导出所有研究主题的关键词和筛选规则",
                format: "JSON",
              },
              {
                title: "对话历史记录",
                description: "导出与 AI 助手的所有对话记录",
                format: "Markdown / JSON",
              },
              {
                title: "阅读历史",
                description: "导出论文浏览和阅读历史记录",
                format: "CSV / JSON",
              },
            ].map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between rounded-lg border border-border p-4"
              >
                <div>
                  <span className="text-sm font-medium">{item.title}</span>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {item.description}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    支持格式：{item.format}
                  </p>
                </div>
                <Button variant="outline" size="sm">
                  <Download className="size-3.5" />
                  导出
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
