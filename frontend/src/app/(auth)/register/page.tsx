"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Mail, Lock, User, BookOpen, ArrowRight } from "lucide-react";
import { register } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (password !== confirmPassword) {
      setError("两次输入的密码不一致");
      setLoading(false);
      return;
    }

    if (password.length < 8) {
      setError("密码长度至少8位");
      setLoading(false);
      return;
    }

    try {
      const data = await register(email, name, password);
      if (data.success) {
        router.push("/login");
      } else {
        setError(data.message || "注册失败，请稍后重试");
      }
    } catch (err: any) {
      setError("网络错误，请稍后重试");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-white p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex size-12 items-center justify-center rounded-xl bg-slate-900">
            <BookOpen className="size-6 text-white" />
          </div>
          <h1 className="text-xl font-bold text-slate-900">PaperFinder</h1>
          <p className="mt-1 text-xs text-slate-500">发现学术前沿，助力科研创新</p>
        </div>

        {/* Register Card */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5">
            <h2 className="text-base font-semibold text-slate-900">注册</h2>
            <p className="mt-0.5 text-xs text-slate-500">创建账号，开始你的研究之旅</p>
          </div>

          {error && (
            <div className="mb-4 rounded-lg bg-red-50 p-2.5 text-xs text-red-600">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div>
              <label htmlFor="name" className="mb-1 block text-xs font-medium text-slate-700">
                用户名
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-slate-400" />
                <Input
                  id="name"
                  type="text"
                  placeholder="你的名字"
                  className="h-9 pl-9 text-sm"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="email" className="mb-1 block text-xs font-medium text-slate-700">
                邮箱
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-slate-400" />
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  className="h-9 pl-9 text-sm"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="mb-1 block text-xs font-medium text-slate-700">
                密码
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-slate-400" />
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••（至少 8 位）"
                  className="h-9 pl-9 text-sm"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </div>
            </div>

            <div>
              <label htmlFor="confirmPassword" className="mb-1 block text-xs font-medium text-slate-700">
                确认密码
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-slate-400" />
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  className="h-9 pl-9 text-sm"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </div>
            </div>

            <Button
              type="submit"
              className="h-9 w-full bg-slate-900 text-sm text-white hover:bg-slate-800"
              disabled={loading}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="size-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  注册中...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  注册
                  <ArrowRight className="size-3.5" />
                </span>
              )}
            </Button>
          </form>

          <div className="mt-4 text-center">
            <p className="text-xs text-slate-500">
              已有账号？{" "}
              <Link href="/login" className="font-medium text-slate-900 hover:underline">
                立即登录
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
