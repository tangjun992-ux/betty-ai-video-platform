"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Locale = "zh" | "en";

export const dictionaries = {
  zh: {
    "nav.home": "首页", "nav.explore": "探索", "nav.feed": "动态", "nav.library": "我的库",
    "nav.projects": "项目", "nav.sessions": "会话", "nav.agent": "AI Agent", "nav.image": "图片创作",
    "nav.video": "视频创作", "nav.imageEdit": "图片编辑", "nav.motion": "动作同步",
    "nav.lipsync": "唇形同步", "nav.avatar": "AI 头像", "nav.timeline": "时间线",
    "nav.upscale": "AI 放大", "nav.removeBg": "去背景", "nav.extend": "AI 扩图",
    "nav.audio": "AI 音频", "nav.extract": "内容提取", "nav.teams": "团队",
    "top.search": "搜索资产、工具或提示词…", "top.create": "立即创作",
    "top.settings": "设置", "top.dashboard": "控制台", "top.billing": "积分中心",
    "top.developer": "开发者 API", "top.logout": "退出登录", "top.login": "登录",
    "top.guest": "访客", "top.language": "English",
    "home.badge": "已验证模型 · 一站式专业创作平台",
    "home.title1": "让每个创意", "home.title2": "一键成片",
    "home.subtitle": "对接已验证顶级模型；只做导演，不写提示词 — 一句话描述，AI 自动规划→生成→精修",
    "home.agent": "Agent", "home.image": "图片", "home.video": "视频",
    "home.placeholderAgent": "一句话说出想要的，例如：做一个 30 秒的咖啡产品宣传片…",
    "home.placeholderImage": "描述你想要创作的图像，越具体越好…",
    "home.placeholderVideo": "描述你想要的视频画面、运镜与时长…",
    "home.startDirect": "开始导演", "home.startCreate": "开始创作",
    "dashboard.greetingMorning": "早上好", "dashboard.greetingAfternoon": "下午好",
    "dashboard.greetingEvening": "晚上好", "dashboard.creator": "创作者",
    "dashboard.question": "今天想创作什么？", "dashboard.recent": "最近创作",
    "dashboard.quick": "快捷工具", "dashboard.all": "查看全部",
    "agent.title": "不写提示词，只做导演",
    "agent.cta": "开始导演",
    "agent.preview": "免费预览成片",
    "agent.real": "真实生成",
    "pricing.title": "灵活定价，适合每个人",
    "pricing.subtitle": "随时按比例调整方案。从入门到专业，按用量计费。",
    "pricing.cta": "立即开始",
    "billing.title": "积分中心",
    "billing.subtitle": "管理你的积分余额、充值与消费流水",
    "billing.cta": "购买积分",
    "library.title": "我的素材库",
    "library.subtitle": "上传、生成与管理你的创作资产",
    "library.cta": "上传素材",
    // ── Image tool studio (upscale / bg-remove / extend / edit) ──
    "tool.upload": "上传图片", "tool.result": "处理结果", "tool.factor": "放大倍率",
    "tool.ratio": "目标画幅", "tool.clickUpload": "点击上传图片",
    "tool.supported": "支持 JPG / PNG / WEBP，≤10MB", "tool.instruction": "编辑指令",
    "tool.processing": "AI 正在处理...", "tool.resultHere": "结果将显示在这里",
    "tool.download": "下载", "tool.needImage": "请上传图片",
    "tool.needImageDesc": "先选择一张要处理的图片", "tool.needPrompt": "请输入指令",
    "tool.needPromptDesc": "描述你想要的修改", "tool.done": "处理完成",
    "tool.doneDesc": "结果已生成，可对比 / 下载", "tool.failed": "处理失败",
    "tool.failedDesc": "请稍后重试",
    "tool.edit.title": "AI 图片编辑器", "tool.edit.subtitle": "Nano Banana 指令编辑 · 换背景 / 改风格 / 加元素 / 局部修改",
    "tool.edit.cta": "应用编辑", "tool.edit.ph": "用一句话描述修改，例如：把背景换成星空夜景，给人物加一副墨镜",
    "tool.upscale.title": "AI 放大", "tool.upscale.subtitle": "Topaz 超分辨率 · 2x / 4x 无损画质提升", "tool.upscale.cta": "开始放大",
    "tool.bg.title": "AI 去背景", "tool.bg.subtitle": "一键抠图 · 生成透明背景 PNG", "tool.bg.cta": "去除背景",
    "tool.extend.title": "AI 扩图", "tool.extend.subtitle": "智能外扩 / 改画幅 · 竖屏转横屏、补全画面边缘",
    "tool.extend.cta": "扩展画面", "tool.extend.ph": "可选：描述扩展区域的内容（留空则自然延展），例如：向两侧延展出更多草地与天空",
  },
  en: {
    "nav.home": "Home", "nav.explore": "Explore", "nav.feed": "Feed", "nav.library": "Library",
    "nav.projects": "Projects", "nav.sessions": "Sessions", "nav.agent": "AI Agent", "nav.image": "Image Creation",
    "nav.video": "Video Creation", "nav.imageEdit": "Image Editor", "nav.motion": "Motion Sync",
    "nav.lipsync": "Lip Sync", "nav.avatar": "AI Avatar", "nav.timeline": "Timeline",
    "nav.upscale": "AI Upscale", "nav.removeBg": "Remove Background", "nav.extend": "AI Extend",
    "nav.audio": "AI Audio", "nav.extract": "Content Extract", "nav.teams": "Teams",
    "top.search": "Search assets, tools, or prompts…", "top.create": "Create",
    "top.settings": "Settings", "top.dashboard": "Dashboard", "top.billing": "Credits",
    "top.developer": "Developer API", "top.logout": "Log out", "top.login": "Log in",
    "top.guest": "Guest", "top.language": "中文",
    "home.badge": "Verified models · one professional creation platform",
    "home.title1": "Turn every idea", "home.title2": "into a finished film",
    "home.subtitle": "Direct, don't prompt. Describe the idea once and AI plans, generates, and refines the whole production.",
    "home.agent": "Agent", "home.image": "Image", "home.video": "Video",
    "home.placeholderAgent": "Describe your idea, e.g. a 30-second cinematic coffee product film…",
    "home.placeholderImage": "Describe the image you want to create…",
    "home.placeholderVideo": "Describe the scene, camera movement, and duration…",
    "home.startDirect": "Start directing", "home.startCreate": "Create",
    "dashboard.greetingMorning": "Good morning", "dashboard.greetingAfternoon": "Good afternoon",
    "dashboard.greetingEvening": "Good evening", "dashboard.creator": "Creator",
    "dashboard.question": "What would you like to create today?", "dashboard.recent": "Recent creations",
    "dashboard.quick": "Quick tools", "dashboard.all": "View all",
    "agent.title": "Direct, don't write prompts",
    "agent.cta": "Start directing",
    "agent.preview": "Free preview",
    "agent.real": "Real generate",
    "pricing.title": "Flexible pricing for everyone",
    "pricing.subtitle": "Scale anytime. From starter to pro — usage-based billing.",
    "pricing.cta": "Get started",
    "billing.title": "Credits",
    "billing.subtitle": "Manage balance, top-ups, and usage history",
    "billing.cta": "Buy credits",
    "library.title": "My library",
    "library.subtitle": "Upload, generate, and manage your creative assets",
    "library.cta": "Upload",
    // ── Image tool studio ──
    "tool.upload": "Upload image", "tool.result": "Result", "tool.factor": "Scale",
    "tool.ratio": "Aspect ratio", "tool.clickUpload": "Click to upload",
    "tool.supported": "JPG / PNG / WEBP, up to 10MB", "tool.instruction": "Edit instruction",
    "tool.processing": "AI is processing...", "tool.resultHere": "Result will appear here",
    "tool.download": "Download", "tool.needImage": "Please upload an image",
    "tool.needImageDesc": "Select an image to process first", "tool.needPrompt": "Enter an instruction",
    "tool.needPromptDesc": "Describe the change you want", "tool.done": "Done",
    "tool.doneDesc": "Result ready — compare / download", "tool.failed": "Failed",
    "tool.failedDesc": "Please try again later",
    "tool.edit.title": "AI Image Editor", "tool.edit.subtitle": "Instruction editing · replace background / restyle / add elements / local edits",
    "tool.edit.cta": "Apply edit", "tool.edit.ph": "Describe the change in one line, e.g. replace the background with a starry night and add sunglasses",
    "tool.upscale.title": "AI Upscale", "tool.upscale.subtitle": "Topaz super-resolution · 2x / 4x lossless enhancement", "tool.upscale.cta": "Upscale",
    "tool.bg.title": "AI Remove Background", "tool.bg.subtitle": "One-click cutout · transparent PNG output", "tool.bg.cta": "Remove background",
    "tool.extend.title": "AI Extend", "tool.extend.subtitle": "Smart outpaint / reframe · portrait→landscape, fill edges",
    "tool.extend.cta": "Extend", "tool.extend.ph": "Optional: describe the extended area (leave blank for natural fill), e.g. extend more grass and sky on both sides",
  },
} as const;

export type TranslationKey = keyof typeof dictionaries.zh;
type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
  t: (key: TranslationKey) => string;
};

const LocaleContext = createContext<LocaleContextValue>({
  locale: "zh", setLocale: () => {}, toggleLocale: () => {}, t: (key) => key,
});

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("zh");
  useEffect(() => {
    // A `?lang=` query wins (real per-locale entry point for hreflang/SEO and
    // shareable localized links), then the persisted preference.
    try {
      const q = new URLSearchParams(window.location.search).get("lang");
      if (q === "en" || q === "zh") {
        setLocaleState(q);
        localStorage.setItem("betty-locale", q);
        return;
      }
    } catch { /* ignore */ }
    const stored = localStorage.getItem("betty-locale");
    if (stored === "en" || stored === "zh") setLocaleState(stored);
  }, []);
  const setLocale = (next: Locale) => {
    setLocaleState(next);
    localStorage.setItem("betty-locale", next);
    document.documentElement.lang = next === "zh" ? "zh-CN" : "en";
  };
  useEffect(() => {
    document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
  }, [locale]);
  const value = useMemo<LocaleContextValue>(() => ({
    locale, setLocale, toggleLocale: () => setLocale(locale === "zh" ? "en" : "zh"),
    t: (key) => dictionaries[locale][key] || dictionaries.zh[key] || key,
  }), [locale]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export const useLocale = () => useContext(LocaleContext);
