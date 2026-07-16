"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Dedicated Product Shots app (Yapper parity) — real workflow via image generate
 * with a product-photography prompt pack (not a dead link).
 */
const PACK =
  "professional product photography, studio softbox lighting, clean seamless backdrop, " +
  "sharp focus, commercial catalog quality, subtle reflections, centered composition";

export default function ProductShotsPage() {
  const router = useRouter();
  useEffect(() => {
    const q = new URLSearchParams({
      tool: "product",
      prompt: PACK,
      model: "gpt-image-2",
    });
    router.replace(`/create/image?${q.toString()}`);
  }, [router]);
  return (
    <div className="max-w-lg mx-auto px-4 py-20 text-center text-sm text-text-secondary">
      正在打开产品摄影工作流…
    </div>
  );
}
