"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  Beaker,
  MessageSquare,
  Star,
  Settings,
} from "lucide-react";

interface MenuItem {
  icon: React.ReactNode;
  label: string;
  href: string;
  badge?: number;
}

const menuItems: MenuItem[] = [
  {
    icon: <FileText className="w-5 h-5" />,
    label: "论文",
    href: "/papers",
  },
  {
    icon: <Beaker className="w-5 h-5" />,
    label: "主题",
    href: "/topics",
  },
  {
    icon: <MessageSquare className="w-5 h-5" />,
    label: "对话",
    href: "/conversations",
  },
  {
    icon: <Star className="w-5 h-5" />,
    label: "收藏",
    href: "/favorites",
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="layout-sidebar bg-background border-r border-border overflow-y-auto">
      <nav className="p-4">
        {/* 主菜单 */}
        <ul className="space-y-1">
          {menuItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-primary-50 text-primary-700"
                      : "text-foreground-secondary hover:bg-background-secondary hover:text-foreground"
                  }`}
                >
                  <span className={isActive ? "text-primary-600" : "text-foreground-muted"}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                  {item.badge && item.badge > 0 && (
                    <span
                      className={`ml-auto px-2 py-0.5 rounded-full text-xs ${
                        isActive
                          ? "bg-primary-100 text-primary-700"
                          : "bg-background-tertiary text-foreground-muted"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* 分隔线 */}
        <div className="my-4 border-t border-border" />

        {/* 设置 */}
        <ul className="space-y-1">
          <li>
            <Link
              href="/settings"
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                pathname === "/settings" || pathname.startsWith("/settings/")
                  ? "bg-primary-50 text-primary-700"
                  : "text-foreground-secondary hover:bg-background-secondary hover:text-foreground"
              }`}
            >
              <span
                className={
                  pathname === "/settings" || pathname.startsWith("/settings/")
                    ? "text-primary-600"
                    : "text-foreground-muted"
                }
              >
                <Settings className="w-5 h-5" />
              </span>
              <span>设置</span>
            </Link>
          </li>
        </ul>
      </nav>

      {/* 底部信息 */}
      <div className="p-4 border-t border-border mt-auto">
        <div className="text-xs text-foreground-muted text-center">
          <p>Paper Finder Agent</p>
          <p className="mt-1">v0.1.0</p>
        </div>
      </div>
    </aside>
  );
}