import Link from "next/link";
import { BrandMark } from "@/components/BrandLogo";

export const metadata = { title: "离线" };

export default function OfflinePage() {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center px-4 text-center">
      <BrandMark className="w-14 h-14 mb-5" />
      <h1 className="text-2xl font-bold text-text-primary mb-2">当前处于离线状态</h1>
      <p className="text-text-secondary text-sm max-w-sm mb-6">
        网络连接似乎断开了。生成与浏览需要联网；已缓存的页面仍可访问。请检查网络后重试。
      </p>
      <Link href="/" className="btn-primary">重新连接</Link>
    </div>
  );
}
