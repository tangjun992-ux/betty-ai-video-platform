"use client";

import ImageToolStudio from "@/components/ImageToolStudio";

export default function ImageEditorPage() {
  return (
    <ImageToolStudio
      operation="edit"
      emoji="🎨"
      title="AI 图片编辑器"
      subtitle="Nano Banana 指令编辑 · 换背景 / 改风格 / 加元素 / 局部修改"
      cta="应用编辑"
      needsPrompt
      promptPlaceholder="用一句话描述修改，例如：把背景换成星空夜景，给人物加一副墨镜"
      ratios={["auto", "1:1", "16:9", "9:16", "4:3", "3:4"]}
    />
  );
}
