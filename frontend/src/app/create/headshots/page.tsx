"use client";

import BatchPhotoStudio from "@/components/BatchPhotoStudio";

// Yapper "Headshots" — Professional Headshots.
export default function HeadshotsPage() {
  return (
    <BatchPhotoStudio
      emoji="👔"
      title="职业头像 · Headshots"
      subtitle="上传自拍，生成适用于 LinkedIn、简历、企业主页的专业头像"
      subjectLabel="人物特征"
      subjectPlaceholder="例如：30 岁男性，短发，戴眼镜，自信微笑"
      allowReference
      cta="生成职业头像"
      packs={[
        { id: "corporate", name: "商务正装", desc: "西装 · 灰蓝背景", promptSuffix: "专业商务头像，深色西装，中性灰蓝背景，柔和布光，锐利对焦，LinkedIn 风格", style: "photographic" },
        { id: "office", name: "现代办公", desc: "虚化办公背景", promptSuffix: "专业头像，现代办公室虚化背景，自然窗光，商务休闲装，亲和专业", style: "photographic" },
        { id: "creative", name: "创意人像", desc: "彩色 · 时尚感", promptSuffix: "创意专业人像，时尚彩色背景，戏剧化布光，杂志封面质感", style: "photographic" },
        { id: "outdoor", name: "户外自然", desc: "自然环境背景", promptSuffix: "专业户外人像，自然环境虚化背景，黄金时刻光线，温暖真实", style: "photographic" },
      ]}
    />
  );
}
