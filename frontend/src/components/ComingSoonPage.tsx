"use client";

import { type ReactNode } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Sparkles, Clock } from "lucide-react";

export type RelatedTool = { label: string; href: string; icon: string };

export function ComingSoonPage({
  emoji,
  title,
  description,
  cta,
  extra,
  relatedTools,
  upcomingFeatures,
}: {
  emoji: string;
  title: string;
  description: string;
  cta: ReactNode;
  extra?: ReactNode;
  relatedTools: RelatedTool[];
  upcomingFeatures: string[];
}) {
  const router = useRouter();

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-cosmic-deep">
      <div className="max-w-2xl mx-auto px-4 py-16 md:py-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="text-center space-y-6"
        >
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
            className="inline-flex items-center justify-center w-24 h-24 rounded-3xl bg-brand-50 border border-cosmic-border shadow-elevation-sm"
          >
            <span className="text-5xl">{emoji}</span>
          </motion.div>

          <div className="space-y-3">
            <h1 className="text-h2 text-text-primary tracking-tight">{title}</h1>
            <p className="text-body text-text-secondary max-w-md mx-auto leading-relaxed">
              {description}
            </p>
          </div>

          <div className="flex items-center justify-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-warning-muted border border-warning/20 text-warning text-caption font-semibold">
              <Clock className="w-3.5 h-3.5" />
              即将推出
            </span>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
            className="pt-2"
          >
            {cta}
          </motion.div>

          {extra}

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.4 }}
            className="pt-8 border-t border-cosmic-border/60"
          >
            <p className="text-caption text-text-tertiary mb-4">相关工具</p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              {relatedTools.map((tool) => (
                <button
                  key={tool.href}
                  onClick={() => router.push(tool.href)}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cosmic-surface border border-cosmic-border text-body-sm text-text-secondary hover:text-text-primary hover:border-cosmic-border-hover hover:shadow-elevation-sm transition-all duration-200"
                >
                  <span>{tool.icon}</span>
                  <span>{tool.label}</span>
                </button>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.4 }}
            className="mt-6 p-6 rounded-2xl bg-cosmic-subtle/50 border border-dashed border-cosmic-border/80 text-left"
          >
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-accent-cyan mt-0.5 flex-shrink-0" />
              <div className="space-y-2">
                <h3 className="text-body-sm font-semibold text-text-primary">功能预告</h3>
                <ul className="space-y-1.5 text-body-sm text-text-secondary">
                  {upcomingFeatures.map((feature) => (
                    <li key={feature} className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan/60 flex-shrink-0" />
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
