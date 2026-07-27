"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import Link from "next/link";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Page error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4">
      <div className="max-w-md w-full text-center space-y-6">
        {/* Icon */}
        <div className="mx-auto w-16 h-16 rounded-2xl bg-destructive/10 flex items-center justify-center">
          <AlertTriangle className="w-8 h-8 text-destructive" />
        </div>

        {/* Message */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-text-accent-cyan">
            出了点问题
          </h1>
          <p className="text-sm text-text-secondary leading-relaxed">
            页面加载时发生了意外错误。请尝试刷新页面，或返回首页。
          </p>
          {error.digest && (
            <p className="text-xs text-text-secondary/60 font-mono">
              Error ID: {error.digest}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-center gap-3 pt-2">
          <button
            onClick={reset}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-accent-cyan-foreground text-sm font-medium hover:bg-accent-cyan/90 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            重试
          </button>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cosmic-surface text-text-accent-cyan text-sm font-medium hover:bg-cosmic-surface/80 transition-colors"
          >
            <Home className="w-4 h-4" />
            返回首页
          </Link>
        </div>
      </div>
    </div>
  );
}
