import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "betty — AI 内容创作平台",
    short_name: "betty",
    description: "一句话成片：对接已验证全球顶级 AI 模型的图片/视频/音频创作平台",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#FCFCFE",
    theme_color: "#0F766E",
    lang: "zh-CN",
    orientation: "portrait-primary",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "AI 导演", short_name: "Agent", url: "/agent" },
      { name: "图片创作", short_name: "图片", url: "/create/image" },
      { name: "探索", short_name: "探索", url: "/explore" },
    ],
    categories: ["productivity", "graphics", "multimedia"],
  };
}
