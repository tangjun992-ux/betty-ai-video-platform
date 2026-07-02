import Link from "next/link";
import { FileQuestion, Home, Search } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4">
      <div className="max-w-md w-full text-center space-y-6">
        {/* Icon */}
        <div className="mx-auto w-16 h-16 rounded-2xl bg-cosmic-surface flex items-center justify-center">
          <FileQuestion className="w-8 h-8 text-text-secondary" />
        </div>

        {/* Message */}
        <div className="space-y-2">
          <h1 className="text-6xl font-bold text-text-accent-cyan/10">404</h1>
          <h2 className="text-2xl font-bold text-text-accent-cyan">
            页面未找到
          </h2>
          <p className="text-sm text-text-secondary leading-relaxed">
            您访问的页面不存在或已被移动。请检查网址是否正确，或返回首页。
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-center gap-3 pt-2">
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-accent-cyan-foreground text-sm font-medium hover:bg-accent-cyan/90 transition-colors"
          >
            <Home className="w-4 h-4" />
            返回首页
          </Link>
          <Link
            href="/tools"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cosmic-surface text-text-accent-cyan text-sm font-medium hover:bg-cosmic-surface/80 transition-colors"
          >
            <Search className="w-4 h-4" />
            探索工具
          </Link>
        </div>
      </div>
    </div>
  );
}
