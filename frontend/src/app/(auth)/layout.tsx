export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 px-4 py-12">
      {/* 背景装饰圆 */}
      <div className="pointer-events-none absolute -left-40 -top-40 size-96 rounded-full bg-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 -right-40 size-96 rounded-full bg-indigo-400/10 blur-3xl" />
      <div className="relative w-full max-w-md">
        {children}
      </div>
    </div>
  );
}
