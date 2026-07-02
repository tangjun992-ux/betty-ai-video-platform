'use client';

import Link from 'next/link';
import type { LucideIcon } from 'lucide-react';

const toneClasses: Record<string, string> = {
  violet:  'bg-violet-100 text-violet-700',
  sky:     'bg-sky-100 text-sky-700',
  blue:    'bg-blue-100 text-blue-700',
  cyan:    'bg-cyan-100 text-cyan-700',
  fuchsia: 'bg-fuchsia-100 text-fuchsia-700',
  zinc:    'bg-zinc-100 text-zinc-700',
  amber:   'bg-amber-100 text-amber-700',
  emerald: 'bg-emerald-100 text-emerald-700',
} as const;

type Tone = keyof typeof toneClasses;

interface ToolPillProps {
  icon: LucideIcon;
  label: string;
  to: string;
  tone: Tone;
}

export function ToolPill({ icon: Icon, label, to, tone }: ToolPillProps) {
  return (
    <Link
      href={to}
      className={`flex flex-col items-center gap-1.5 rounded-xl p-3 transition-transform hover:scale-[1.03] ${toneClasses[tone] ?? toneClasses.zinc}`}
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/50">
        <Icon className="h-5 w-5" />
      </div>
      <span className="text-xs font-medium">{label}</span>
    </Link>
  );
}
