"use client";

import ImageToolStudio from "@/components/ImageToolStudio";

export default function UpscalePage() {
  return (
    <ImageToolStudio
      operation="upscale"
      emoji="🔍"
      title="AI 放大"
      subtitle="Topaz 超分辨率 · 2x / 4x 无损画质提升"
      cta="开始放大"
      titleKey="tool.upscale.title"
      subtitleKey="tool.upscale.subtitle"
      ctaKey="tool.upscale.cta"
      factors={["2", "4"]}
    />
  );
}
