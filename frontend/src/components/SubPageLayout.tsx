"use client";
import Link from "next/link";
import { CreditsBadge } from "@/components/CreditsBadge";

export default function SubPageLayout({ children, title }: { children: React.ReactNode; title?: string }) {
  return (
    <div className="min-h-screen bg-cosmic-deep">
      <header className="sticky top-0 z-50 bg-cosmic-surface/80 backdrop-blur-sm border-b border-cosmic-border">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-semibold text-sm">
            <div className="w-6 h-6 bg-gradient-to-br from-accent-cyan to-accent-violet rounded flex items-center justify-center text-xs">🎬</div>
            AI 视频创作
          </Link>
          <nav className="flex items-center gap-4 text-xs text-text-secondary">
            <Link href="/" className="hover:text-text-primary transition">创作</Link>
            <Link href="/gallery" className="hover:text-text-primary transition">画廊</Link>
            <Link href="/pricing" className="hover:text-text-primary transition">定价</Link>
            <CreditsBadge />
          </nav>
        </div>
      </header>
      {title && (
        <div className="text-center pt-6 pb-2">
          <h1 className="text-xl font-bold">{title}</h1>
        </div>
      )}
      {children}
    </div>
  );
}
