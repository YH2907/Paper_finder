"use client";

import { useState } from "react";
import {
  Search,
  ChevronDown,
  User,
  Settings,
  LogOut,
  BookOpen,
  Command,
} from "lucide-react";

export function Header() {
  const [showUserMenu, setShowUserMenu] = useState(false);

  return (
    <header className="layout-header bg-background border-b border-border px-4 flex items-center justify-between">
      {/* Logo */}
      <div className="flex items-center gap-2">
        <BookOpen className="w-6 h-6 text-primary-600" />
        <span className="text-lg font-semibold text-foreground">Paper Finder</span>
      </div>

      {/* 搜索栏 */}
      <div className="flex-1 max-w-md mx-8">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-foreground-muted" />
          <input
            type="text"
            placeholder="搜索论文、主题、对话..."
            className="w-full pl-10 pr-20 py-2 bg-background-secondary border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center gap-1 text-xs text-foreground-muted">
            <kbd className="px-1.5 py-0.5 bg-background-tertiary rounded border border-border">
              <Command className="w-3 h-3 inline" />
            </kbd>
            <span>K</span>
          </div>
        </div>
      </div>

      {/* 右侧操作区 */}
      <div className="flex items-center gap-4">

        {/* 用户菜单 */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 p-2 rounded-lg hover:bg-background-secondary transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
              <User className="w-4 h-4 text-primary-600" />
            </div>
            <span className="text-sm font-medium">用户</span>
            <ChevronDown className="w-4 h-4 text-foreground-muted" />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 top-full mt-2 w-48 bg-background rounded-lg shadow-lg border border-border py-1 z-50">
              <div className="px-4 py-2 border-b border-border">
                <p className="text-sm font-medium">用户名</p>
                <p className="text-xs text-foreground-muted">user@example.com</p>
              </div>
              <button className="w-full px-4 py-2 text-left text-sm hover:bg-background-secondary flex items-center gap-2">
                <User className="w-4 h-4" />
                个人资料
              </button>
              <button className="w-full px-4 py-2 text-left text-sm hover:bg-background-secondary flex items-center gap-2">
                <Settings className="w-4 h-4" />
                设置
              </button>
              <div className="border-t border-border">
                <button className="w-full px-4 py-2 text-left text-sm hover:bg-background-secondary flex items-center gap-2 text-error">
                  <LogOut className="w-4 h-4" />
                  退出登录
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}