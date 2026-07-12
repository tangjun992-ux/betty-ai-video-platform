"use client";

import ImageToolStudio from "@/components/ImageToolStudio";

export default function ExtendPage() {
  return (
    <ImageToolStudio
      operation="extend"
      emoji="🖼️"
      title="AI 扩图"
      subtitle="智能外扩 / 改画幅 · 竖屏转横屏、补全画面边缘"
      cta="扩展画面"
      needsPrompt
      promptPlaceholder="可选：描述扩展区域的内容（留空则自然延展），例如：向两侧延展出更多草地与天空"
      ratios={["16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]}
    />
  );
}
