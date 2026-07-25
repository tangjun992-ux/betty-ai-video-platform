"use client";

import { useRouter } from "next/navigation";
import { ArrowRight, Mic } from "lucide-react";
import { useCreationStore } from "@/lib/stores";
import { ComingSoonPage } from "@/components/ComingSoonPage";

export default function AvatarPage() {
  const router = useRouter();
  const { setPrompt } = useCreationStore();

  return (
    <ComingSoonPage
      emoji="👤"
      title="AI 头像"
      description="上传一张照片和一段音频，生成说话视频。让静态肖像开口说话，适用于虚拟主播、数字人播报等场景。"
      cta={
        <button
          onClick={() => {
            setPrompt("生成头像说话视频");
            router.push("/create/lipsync");
          }}
          className="btn-primary text-base px-8 py-3 h-auto gap-2"
        >
          <Mic className="w-4 h-4" />
          跳转到唇形同步
          <ArrowRight className="w-4 h-4" />
        </button>
      }
      relatedTools={[
        { label: "唇形同步", href: "/create/lipsync", icon: "🎤" },
        { label: "动态同步", href: "/create/motion", icon: "🎬" },
        { label: "图片创作", href: "/create/image", icon: "🖼️" },
      ]}
      upcomingFeatures={[
        "上传任意肖像照片，AI 自动识别面部特征",
        "支持文本转语音或上传自定义音频",
        "生成自然的口型同步视频，支持多种语言",
        "输出 1080p 高清视频，适用于社交媒体",
      ]}
    />
  );
}
