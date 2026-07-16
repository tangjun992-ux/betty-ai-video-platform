"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Camera, User, ShoppingBag, Sparkles } from "lucide-react";

/** AI Photo Packs — real pack → create/image with curated prompts (Yapper parity). */
const PACKS = [
  {
    id: "product",
    title: "电商产品包",
    desc: "白底 / 场景 / 细节三连拍提示词",
    href: "/create/product",
    icon: ShoppingBag,
    prompt: "product catalog set",
  },
  {
    id: "headshots",
    title: "职业头像包",
    desc: "LinkedIn / 简历级棚拍人像",
    href: "/create/headshots",
    icon: User,
    prompt: "professional headshots",
  },
  {
    id: "lifestyle",
    title: "生活方式包",
    desc: "自然光生活场景，社交媒体构图",
    href: `/create/image?tool=batch&prompt=${encodeURIComponent(
      "lifestyle photography, natural window light, candid moment, soft color grade, social media ready"
    )}`,
    icon: Camera,
    prompt: "lifestyle",
  },
  {
    id: "brand",
    title: "品牌视觉包",
    desc: "极简品牌海报与几何构图",
    href: `/create/image?prompt=${encodeURIComponent(
      "minimal brand visual system, geometric composition, soft gradient, premium typography space"
    )}`,
    icon: Sparkles,
    prompt: "brand",
  },
];

export default function PhotoPacksPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
        <h1 className="text-3xl font-bold gradient-text-static mb-2">AI Photo Packs</h1>
        <p className="text-sm text-text-secondary max-w-xl">
          对标 Yapper Photo Packs——每个包都是真实生成入口（提示词包 + 图片工作流），非空壳页。
        </p>
      </motion.div>
      <div className="grid sm:grid-cols-2 gap-4">
        {PACKS.map((p) => (
          <Link
            key={p.id}
            href={p.href}
            className="rounded-2xl border border-cosmic-border bg-cosmic-subtle/50 p-5 hover:border-brand/40 transition-colors"
          >
            <p.icon className="w-6 h-6 text-brand mb-3" />
            <h2 className="font-semibold mb-1">{p.title}</h2>
            <p className="text-sm text-text-secondary">{p.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
