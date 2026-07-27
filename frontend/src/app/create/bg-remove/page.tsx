"use client";

import ImageToolStudio from "@/components/ImageToolStudio";

export default function BgRemovePage() {
  return (
    <ImageToolStudio
      operation="bg-remove"
      emoji="✂️"
      title="AI 去背景"
      subtitle="智能识别主体，一键抠图 · 电商 / 证件 / 设计素材"
      cta="去除背景"
    />
  );
}
