"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

const PACK =
  "professional LinkedIn headshot, soft studio lighting, neutral gray backdrop, " +
  "sharp eyes, natural skin texture, business attire, 85mm portrait, confident expression";

export default function HeadshotsPage() {
  const router = useRouter();
  useEffect(() => {
    const q = new URLSearchParams({
      tool: "avatar",
      prompt: PACK,
      model: "gpt-image-2",
    });
    router.replace(`/create/image?${q.toString()}`);
  }, [router]);
  return (
    <div className="max-w-lg mx-auto px-4 py-20 text-center text-sm text-text-secondary">
      正在打开职业头像工作流…
    </div>
  );
}
