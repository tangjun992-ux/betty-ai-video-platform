"use client";

import { BatchPackStudio } from "@/components/BatchPackStudio";

/** Professional Headshots — real batch SKU pipeline (对标 Yapper Headshots). */
export default function HeadshotsPage() {
  return (
    <BatchPackStudio
      defaultPack="headshots"
      category="portrait"
      title="专业头像批量生成"
      subtitle="上传一张自拍或描述人物，一键生成商务 / LinkedIn / 证件 / 创意专业头像套系。"
      subjectPlaceholder="例如：一位年轻的亚洲女性 / 一位戴眼镜的男性工程师"
    />
  );
}
