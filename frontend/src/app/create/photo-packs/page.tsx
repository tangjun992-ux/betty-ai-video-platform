"use client";

import { BatchPackStudio } from "@/components/BatchPackStudio";

/** AI Photo Packs — real batch SKU pipelines (对标 Yapper Photo Packs). */
export default function PhotoPacksPage() {
  return (
    <BatchPackStudio
      title="AI 照片包"
      subtitle="选择一个套系，一键批量生成成套风格照片。产品 / 头像 / 生活方式 / 品牌视觉均为真实生成。"
      subjectPlaceholder="描述你的主体或主题（可选）"
    />
  );
}
