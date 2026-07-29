"use client";

import { BatchPackStudio } from "@/components/BatchPackStudio";

/** Product Shots — real batch SKU pipeline (对标 Yapper Product Shots). */
export default function ProductShotsPage() {
  return (
    <BatchPackStudio
      defaultPack="product"
      category="product"
      title="产品图批量生成"
      subtitle="上传一张产品图或描述主体，一键生成白底 / 角度 / 细节 / 场景多图套系。"
      subjectPlaceholder="例如：一瓶蓝色渐变的香水 / 一双白色运动鞋"
    />
  );
}
