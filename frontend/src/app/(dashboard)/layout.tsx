"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { ResearchProvider } from "@/contexts/ResearchContext";
import {
  BookOpen,
  MessageSquare,
  Bookmark,
  Settings,
  FileText,
  User,
  LogIn,
  LogOut,
  PanelLeftClose,
  PanelLeft,
  Menu,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const navItems = [
  { href: "/", label: "论文发现", icon: FileText },
  { href: "/papers", label: "论文列表", icon: FileText },
  { href: "/topics", label: "研究主题", icon: BookOpen },
  { href: "/chat", label: "AI 对话", icon: MessageSquare },
  { href: "/bookmarks", label: "收藏夹", icon: Bookmark },
  { href: "/settings", label: "设置", icon: Settings },
];

const COLLAPSED_WIDTH = 64;
const DEFAULT_WIDTH = 224;

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, isAuthenticated } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(DEFAULT_WIDTH);
  const isResizing = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const handleResizeStart = useCallback(
    (e: React.MouseEvent) => {
      isResizing.current = true;
      startX.current = e.clientX;
      startWidth.current = sidebarWidth;
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";

      const handleMouseMove = (e: MouseEvent) => {
        if (!isResizing.current) return;
        const diff = e.clientX - startX.current;
        const newWidth = Math.max(180, Math.min(320, startWidth.current + diff));
        setSidebarWidth(newWidth);
      };

      const handleMouseUp = () => {
        isResizing.current = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };

      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    },
    [sidebarWidth]
  );

  const currentWidth = collapsed ? COLLAPSED_WIDTH : sidebarWidth;

  return (
    <ResearchProvider>
      <div className="flex h-screen overflow-hidden bg-background">
        {/* Desktop sidebar */}
        <aside
          className="hidden md:flex flex-col border-r border-border bg-card transition-all duration-300 relative"
          style={{ width: currentWidth }}
        >
          {/* Logo */}
          <div className="flex h-14 items-center border-b border-border px-4">
            {!collapsed && (
              <Link href="/" className="flex items-center gap-2 font-bold text-lg">
                📚 Paper Finder
              </Link>
            )}
          </div>

          {/* Nav */}
          <nav className="flex-1 overflow-y-auto p-2 space-y-1">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                  title={collapsed ? item.label : undefined}
                >
                  <item.icon className="size-4 shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              );
            })}
          </nav>

          {/* User section */}
          <div className="border-t border-border p-3">
            {isAuthenticated ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <div className="size-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <User className="size-4 text-primary" />
                  </div>
                  {!collapsed && (
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{user?.name}</p>
                      <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                    </div>
                  )}
                </div>
                {!collapsed && (
                  <Button variant="outline" size="sm" className="w-full" onClick={handleLogout}>
                    <LogOut className="size-4 mr-2" />
                    退出登录
                  </Button>
                )}
              </div>
            ) : (
              <>
                <Link href="/login">
                  <Button variant="outline" className="w-full justify-start gap-2">
                    <LogIn className="size-4" />
                    {!collapsed && "登录"}
                  </Button>
                </Link>
              </>
            )}
          </div>

          {/* Resize handle */}
          {!collapsed && (
            <div
              className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/20 transition-colors"
              onMouseDown={handleResizeStart}
            />
          )}
        </aside>

        {/* Mobile overlay */}
        {mobileOpen && (
          <div className="fixed inset-0 z-40 bg-black/50 md:hidden" onClick={() => setMobileOpen(false)} />
        )}

        {/* Mobile sidebar */}
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-50 w-72 bg-card border-r border-border transform transition-transform duration-300 md:hidden",
            mobileOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          <div className="flex h-14 items-center justify-between border-b border-border px-4">
            <Link href="/" className="flex items-center gap-2 font-bold text-lg">
              📚 Paper Finder
            </Link>
            <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)}>
              <X className="size-5" />
            </Button>
          </div>
          <nav className="flex-1 overflow-y-auto p-2 space-y-1">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  <item.icon className="size-4 shrink-0" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
          <div className="border-t border-border p-3">
            {isAuthenticated ? (
              <Button variant="outline" size="sm" className="w-full" onClick={handleLogout}>
                <LogOut className="size-4 mr-2" />
                退出登录
              </Button>
            ) : (
              <Link href="/login">
                <Button variant="outline" className="w-full justify-start gap-2">
                  <LogIn className="size-4" />
                  登录
                </Button>
              </Link>
            )}
          </div>
        </aside>

        {/* Main content */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Top bar */}
          <header className="flex h-14 items-center border-b border-border bg-card px-4 md:px-6">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden size-8 mr-2"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="size-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="hidden md:flex size-8 mr-2"
              onClick={() => setCollapsed(!collapsed)}
              title={collapsed ? "展开侧边栏" : "折叠侧边栏"}
            >
              {collapsed ? <PanelLeft className="size-4" /> : <PanelLeftClose className="size-4" />}
            </Button>
            <div className="flex-1" />

          </header>

          {/* Page content */}
          <main className="flex-1 overflow-y-auto">{children}</main>
        </div>
      </div>
    </ResearchProvider>
  );
}
