"use client";

import BatchPhotoStudio from "@/components/BatchPhotoStudio";

// Yapper "Photo Packs" — AI Photo Packs (themed sets).
export default function PhotoPacksPage() {
  return (
    <BatchPhotoStudio
      emoji="🎞️"
      title="写真包 · Photo Packs"
      subtitle="选择主题风格包，一次生成一整套风格统一的写真"
      subjectLabel="主体描述"
      subjectPlaceholder="例如：一位长发女性，或：一只橘猫"
      allowReference
      cta="生成写真包"
      packs={[
        { id: "cinematic", name: "电影质感", desc: "胶片色调 · 光影", promptSuffix: "电影感写真，胶片色调，戏剧化光影，浅景深，35mm 质感", style: "cinematic" },
        { id: "vintage", name: "复古胶片", desc: "70s 暖色颗粒", promptSuffix: "复古胶片写真，70 年代暖色调，柔和颗粒，怀旧氛围", style: "vintage" },
        { id: "fashion", name: "时尚大片", desc: "杂志编辑风", promptSuffix: "时尚编辑写真，高级时装大片，工作室布光，杂志封面构图", style: "editorial" },
        { id: "anime", name: "二次元", desc: "日系动漫风", promptSuffix: "日系动漫风格写真，鲜明色彩，精致光影，插画质感", style: "anime" },
      ]}
    />
  );
}
