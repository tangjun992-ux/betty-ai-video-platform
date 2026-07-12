"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Locale = "zh" | "en";

export const dictionaries = {
  zh: {
    "nav.home": "首页", "nav.explore": "探索", "nav.feed": "动态", "nav.library": "我的库",
    "nav.projects": "项目", "nav.agent": "AI Agent", "nav.image": "图片创作",
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
  },
  en: {
    "nav.home": "Home", "nav.explore": "Explore", "nav.feed": "Feed", "nav.library": "Library",
    "nav.projects": "Projects", "nav.agent": "AI Agent", "nav.image": "Image Creation",
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
