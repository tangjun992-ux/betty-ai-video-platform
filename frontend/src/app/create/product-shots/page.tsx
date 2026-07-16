"use client";

import BatchPhotoStudio from "@/components/BatchPhotoStudio";

// Yapper "Product Shots" — Stunning Product Shots.
export default function ProductShotsPage() {
  return (
    <BatchPhotoStudio
      emoji="📦"
      title="产品图 · Product Shots"
      subtitle="上传或描述你的产品，一键生成多张专业级商业产品图"
      subjectLabel="产品描述"
      subjectPlaceholder="例如：一瓶琥珀色香水，磨砂玻璃瓶身，金属瓶盖"
      allowReference
      cta="生成产品图"
      packs={[
        { id: "studio", name: "纯色影棚", desc: "白色背景 · 专业布光", promptSuffix: "专业产品摄影，纯白背景，柔和影棚灯光，高清细节，商业级质感", style: "photographic" },
        { id: "lifestyle", name: "生活场景", desc: "真实使用场景", promptSuffix: "生活方式产品摄影，自然光，真实使用场景，浅景深，高级感", style: "photographic" },
        { id: "gradient", name: "渐变背景", desc: "品牌色彩背景", promptSuffix: "产品摄影，柔和渐变背景，居中构图，倒影，现代广告风格", style: "photographic" },
        { id: "nature", name: "自然材质", desc: "石材/木质/织物", promptSuffix: "产品摄影，天然石材与木质台面，柔和自然光，质感丰富，杂志级", style: "photographic" },
      ]}
    />
  );
}
