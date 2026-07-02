import type { Metadata } from "next";
import dynamic from "next/dynamic";
import { Inter } from "next/font/google";
import { cn } from "@/lib/utils";
import "./globals.css";
import { ThemeScript } from "@/components/ThemeScript";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://betty.ai";

export const metadata: Metadata = {
  metadataBase: new URL(baseUrl),
  title: {
    default: "betty — AI 内容创作平台",
    template: "%s | betty",
  },
  description:
    "AI 驱动的图片与视频生成平台。支持 GPT Image 2、Seedance 2.0 等多模型智能路由，轻松创作高质量视觉内容。",
  keywords: ["AI图片生成", "AI视频生成", "AI创作", "Seedance", "GPT Image"],
  authors: [{ name: "betty", url: baseUrl }],
  creator: "betty",
  publisher: "betty",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  alternates: {
    canonical: baseUrl,
  },
  openGraph: {
    title: "betty — AI 内容创作平台",
    description: "AI 驱动的图片与视频生成平台",
    url: baseUrl,
    siteName: "betty",
    locale: "zh_CN",
    type: "website",
    images: [
      {
        url: `${baseUrl}/brand/og-image.png`,
        width: 1200,
        height: 630,
        alt: "betty — AI 内容创作平台",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "betty — AI 内容创作平台",
    description: "AI 驱动的图片与视频生成平台",
    images: [`${baseUrl}/brand/og-image.png`],
    creator: "@betty_ai",
  },
};

// Dynamically import heavy client components with code-splitting
const ClientLayout = dynamic(
  () => import("@/components/ClientLayout").then((mod) => ({ default: mod.ClientLayout })),
  {
    ssr: true,
    loading: () => (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-pulse space-y-4">
          <div className="mx-auto h-10 w-10 rounded-full bg-muted" />
          <div className="h-4 w-32 rounded bg-muted mx-auto" />
        </div>
      </div>
    ),
  }
);

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body className={cn("min-h-screen bg-cosmic-deep antialiased", inter.variable, "font-sans")}>
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
