"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { BrandMark } from "@/components/BrandLogo";

export interface LegalSection { h: string; body: React.ReactNode; }

export function LegalDoc({ title, updated, intro, sections }: {
  title: string;
  updated: string;
  intro?: React.ReactNode;
  sections: LegalSection[];
}) {
  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary mb-6">
        <ArrowLeft className="w-4 h-4" /> 返回首页
      </Link>
      <div className="flex items-center gap-2.5 mb-2">
        <BrandMark className="w-8 h-8" />
        <h1 className="text-3xl font-bold text-text-primary tracking-tight">{title}</h1>
      </div>
      <p className="text-xs text-text-tertiary mb-8">最后更新：{updated}</p>
      {intro && <p className="text-body text-text-secondary leading-relaxed mb-8">{intro}</p>}
      <div className="space-y-8">
        {sections.map((s, i) => (
          <section key={i} className="scroll-mt-24" id={`s${i + 1}`}>
            <h2 className="text-lg font-semibold text-text-primary mb-2.5">{i + 1}. {s.h}</h2>
            <div className="text-body-sm text-text-secondary leading-relaxed space-y-2">{s.body}</div>
          </section>
        ))}
      </div>
      <div className="mt-12 pt-6 border-t border-cosmic-border text-xs text-text-tertiary">
        相关文档：
        <Link href="/terms" className="text-brand hover:underline mx-1.5">服务条款</Link>·
        <Link href="/privacy" className="text-brand hover:underline mx-1.5">隐私政策</Link>·
        <Link href="/content-policy" className="text-brand hover:underline mx-1.5">内容政策</Link>
      </div>
    </div>
  );
}
