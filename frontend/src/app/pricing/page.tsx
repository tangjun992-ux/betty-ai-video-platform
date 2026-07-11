"use client";

import { motion } from "framer-motion";
import { Check, ChevronDown, Info, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { checkout } from "@/lib/api";
import { useToast } from "@/components/Toast";

// 前 3 档固定，对齐 yapper: Starter 1k / Personal 3k / Creator 7k(Most Popular)
const PLANS = [
  {
    id: "starter", name: "Starter", priceMonthly: 9.99, priceYearly: 7.99, credits: 1000, popular: false,
    color: "from-slate-500 to-slate-400",
    features: ["1,000 Credits / 月", "16+ 专业图片模型", "1080p 分辨率", "标准生成速度", "高级唇形同步", "个人使用许可"],
  },
  {
    id: "personal", name: "Personal", priceMonthly: 24.99, priceYearly: 19.99, credits: 3000, popular: false,
    color: "from-violet-500 to-purple-500",
    features: ["3,000 Credits / 月", "23+ 专业视频模型", "Seedance 2.0 全模态", "4K 分辨率", "高级运动控制", "图片 & 视频放大"],
  },
  {
    id: "creator", name: "Creator", priceMonthly: 49.99, priceYearly: 39.99, credits: 7000, popular: true,
    color: "from-brand to-accent-violet",
    features: ["7,000 Credits / 月", "全部 37 个模型", "4K 分辨率 · 最快速度", "商业授权许可", "团队协作", "API 访问", "优先支持"],
  },
];

// 第 4 档 Max：credits 滑块 (对齐 yapper Max 15k→150k)
const MAX_TIERS = [
  { credits: 15000, monthly: 99.99, yearly: 79.99 },
  { credits: 22500, monthly: 139.99, yearly: 111.99 },
  { credits: 37500, monthly: 219.99, yearly: 175.99 },
  { credits: 75000, monthly: 399.99, yearly: 319.99 },
  { credits: 150000, monthly: 749.99, yearly: 599.99 },
];

const CREDIT_USAGE = [
  { model: "GPT Image 2 / Nano Banana", type: "图片", quality: "标准", credits: 2 },
  { model: "FLUX 1.1 Pro / Imagen 4", type: "图片", quality: "高清 4K", credits: 5 },
  { model: "Seedance 2.0 Fast", type: "视频", quality: "5s 1080p", credits: 3 },
  { model: "Seedance 2.0 / Kling 2.5", type: "视频", quality: "5s 1080p", credits: 7 },
  { model: "Veo 3.1 / Sora 2", type: "视频", quality: "5s 旗舰", credits: 12 },
  { model: "Runway Gen-4", type: "视频", quality: "5s 4K", credits: 10 },
];

const FAQS = [
  { q: "Credits 是什么？", a: "Credits 是媒体生成的计费单位，消耗量取决于模型、时长、分辨率等。生成前会明确显示所需 Credits。图片通常比视频便宜。" },
  { q: "未用完的 Credits 会累积吗？", a: "会。每月 Credits 在计费周期开始时发放，未使用部分可累积至下月，上限约为月额度的 2 倍，外加任何一次性购买的 Credits。" },
  { q: "如何获得更多 Credits？", a: "Credits 按订阅档位每月发放。升级更高档位可立即获得新旧档位差额的 Credits（按比例计费）。也可随时在定价页购买一次性 Credits 充值包。" },
  { q: "可以随时升级或降级吗？", a: "可以。升级按剩余时间比例计费并立即生效，降级在下个计费周期生效。随时可在账户页调整。" },
  { q: "支付安全吗？", a: "我们使用 Stripe 处理支付，不存储任何卡片信息，享受银行级安全标准，支付后自动开具收据与发票。" },
  { q: "我的数据和作品是私密的吗？", a: "是。你创建的视频、上传的模型均保持私密，安全存储，受保护免遭未授权访问。" },
];

export default function PricingPage() {
  const router = useRouter();
  const toast = useToast();
  const [busy, setBusy] = useState<string | null>(null);
  const [yearly, setYearly] = useState(false);

  const subscribe = async (planId: string) => {
    setBusy(planId);
    try {
      const r = await checkout("plan", planId, yearly ? "yearly" : "monthly");
      if (r.mode === "dev") {
        toast.success("订阅成功", `+${r.credits_added} 积分已到账`);
        router.push("/billing");
      }
    } catch (e: any) {
      toast.error("订阅失败", e.message || "");
    } finally {
      setBusy(null);
    }
  };
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [maxIdx, setMaxIdx] = useState(1); // 默认 22.5k (yapper Best Value)
  const maxTier = MAX_TIERS[maxIdx];
  const fmt = (n: number) => `$${n.toFixed(2)}`;

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      {/* Hero */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
        <h1 className="text-3xl md:text-4xl font-bold mb-3 text-text-accent-cyan">灵活定价，适合每个人</h1>
        <p className="text-text-secondary max-w-lg mx-auto mb-8">随时按比例调整方案。从入门到专业，按需付费。</p>
        <div role="radiogroup" aria-label="计费周期" className="inline-flex items-center gap-3 p-1 rounded-full bg-cosmic-subtle border border-cosmic-border">
          <button role="radio" aria-checked={!yearly} onClick={() => setYearly(false)}
            className={`px-5 py-2 rounded-full text-sm font-semibold transition-all ${!yearly ? "bg-brand text-white shadow-button-glow" : "text-text-secondary hover:text-brand"}`}>月付</button>
          <button role="radio" aria-checked={yearly} onClick={() => setYearly(true)}
            className={`px-5 py-2 rounded-full text-sm font-semibold transition-all flex items-center gap-1.5 ${yearly ? "bg-brand text-white shadow-button-glow" : "text-text-secondary hover:text-brand"}`}>
            年付<span className="badge-success text-[10px]">省 20%</span>
          </button>
        </div>
      </motion.div>

      {/* "All plans include" Banner — 对齐 yapper.so */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
        className="mb-10 p-6 rounded-2xl border border-cosmic-border bg-cosmic-subtle">
        <p className="text-sm text-text-secondary text-center">所有计划均包含：</p>
        <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 mt-3 text-sm text-text-primary font-medium">
          <span>✅ Seedance 2.0 Omni</span>
          <span>✅ 全部 16+ 图片模型</span>
          <span>✅ 全部 24+ 视频模型</span>
          <span>✅ 唇形同步 & 运动控制</span>
          <span>✅ 商业使用授权</span>
          <span>✅ 优先支持</span>
        </div>
      </motion.div>

      {/* Plans */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-16">
        {PLANS.map((plan, i) => (
          <motion.div key={plan.name} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
            className={`relative rounded-2xl border p-6 flex flex-col transition-all ${
              plan.popular ? "border-brand bg-brand-soft ring-1 ring-brand/20 shadow-button-glow" : "border-cosmic-border bg-cosmic-surface hover:border-cosmic-border-hover"}`}>
            {plan.popular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-brand text-white text-xs font-semibold shadow-button-glow">Most Popular</div>
            )}
            <div className="flex items-center gap-2.5 mb-4">
              <div className={`w-2 h-2 rounded-full bg-gradient-to-br ${plan.color}`} />
              <h3 className="text-lg font-bold text-text-accent-cyan">{plan.name}</h3>
            </div>
            <div className="flex items-baseline gap-1 mb-1">
              <span className="text-3xl font-bold text-text-accent-cyan">{fmt(yearly ? plan.priceYearly : plan.priceMonthly)}</span>
              <span className="text-sm text-text-secondary">/月</span>
            </div>
            {yearly && <p className="text-xs text-brand mb-2">按年计费 ${(plan.priceYearly * 12).toFixed(0)}/年</p>}
            <p className="text-sm text-text-secondary mb-4">{plan.credits.toLocaleString()} Credits / 月</p>
            <ul className="space-y-2.5 mb-6 flex-1">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm">
                  <Check className="w-4 h-4 text-brand flex-shrink-0 mt-0.5" /><span className="text-text-secondary">{f}</span>
                </li>
              ))}
            </ul>
            <button onClick={() => subscribe(plan.id)} disabled={!!busy}
              className={`w-full py-2.5 rounded-xl text-sm font-semibold text-center transition-all active:scale-[0.98] inline-flex items-center justify-center gap-1.5 disabled:opacity-60 ${
              plan.popular ? "bg-brand text-white hover:bg-brand-strong shadow-button-glow" : "bg-cosmic-subtle border border-cosmic-border text-text-primary hover:bg-cosmic-border"}`}>
              {busy === plan.id && <Loader2 className="w-4 h-4 animate-spin" />}
              {plan.popular ? "立即开始" : `选择 ${plan.name}`}
            </button>
          </motion.div>
        ))}

        {/* Max — credits slider */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.24 }}
          className="relative rounded-2xl border border-amber-500/25 bg-amber-500/[0.03] p-6 flex flex-col">
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-amber-500 text-black text-xs font-semibold shadow-lg">Best Value</div>
          <div className="flex items-center gap-2.5 mb-4">
            <div className="w-2 h-2 rounded-full bg-gradient-to-br from-amber-500 to-orange-500" />
            <h3 className="text-lg font-bold text-text-accent-cyan">Max</h3>
          </div>
          <div className="flex items-baseline gap-1 mb-1">
            <span className="text-3xl font-bold text-text-accent-cyan">{fmt(yearly ? maxTier.yearly : maxTier.monthly)}</span>
            <span className="text-sm text-text-secondary">/月</span>
          </div>
          {yearly && <p className="text-xs text-amber-600 mb-2">按年计费 ${(maxTier.yearly * 12).toFixed(0)}/年</p>}
          <p className="text-sm text-text-secondary mb-3">{maxTier.credits.toLocaleString()} Credits / 月</p>
          {/* Slider */}
          <input type="range" min={0} max={MAX_TIERS.length - 1} step={1} value={maxIdx}
            onChange={(e) => setMaxIdx(+e.target.value)}
            className="w-full accent-amber-500 mb-1 cursor-pointer" />
          <div className="flex justify-between text-[10px] text-text-secondary mb-5">
            {MAX_TIERS.map((t) => <span key={t.credits}>{t.credits >= 1000 ? `${t.credits / 1000}k` : t.credits}</span>)}
          </div>
          <ul className="space-y-2.5 mb-6 flex-1">
            {["全部 37 个模型 + 抢先体验", "最高并发 · 8K 分辨率", "无限团队座位", "API + Webhook", "专属客户经理 · SLA"].map((f) => (
              <li key={f} className="flex items-start gap-2 text-sm">
                <Check className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" /><span className="text-text-secondary">{f}</span>
              </li>
            ))}
          </ul>
          <button onClick={() => subscribe("pro")} disabled={!!busy}
            className="w-full py-2.5 rounded-xl text-sm font-semibold text-center bg-amber-500/[0.06] border border-amber-500/30 text-amber-600 hover:bg-amber-500/[0.12] transition-all active:scale-[0.98] inline-flex items-center justify-center gap-1.5 disabled:opacity-60">
            {busy === "pro" && <Loader2 className="w-4 h-4 animate-spin" />}
            选择 Max
          </button>
        </motion.div>

        {/* 积分加购包（Max 专属） */}
        <div className="mt-8 text-center lg:col-span-4">
          <p className="text-sm text-text-secondary mb-3">积分加购包（Max 专属）</p>
          <div className="flex flex-wrap justify-center gap-2">
            {["15k", "22k", "37k", "75k", "150k"].map(s => (
              <span key={s} className="px-3 py-1.5 rounded-lg border border-cosmic-border text-sm text-text-secondary">{s} Credits</span>
            ))}
          </div>
        </div>
      </div>

      {/* Credit Usage Table */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="max-w-3xl mx-auto mb-16">
        <h2 className="text-xl font-bold mb-4 text-center text-text-accent-cyan">Credits 消耗参考</h2>
        <div className="rounded-2xl border border-cosmic-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-cosmic-border bg-cosmic-subtle">
                <th className="text-left px-5 py-3 font-medium text-text-secondary">模型</th>
                <th className="text-left px-5 py-3 font-medium text-text-secondary">类型</th>
                <th className="text-left px-5 py-3 font-medium text-text-secondary">规格</th>
                <th className="text-right px-5 py-3 font-medium text-text-secondary">Credits</th>
              </tr>
            </thead>
            <tbody>
              {CREDIT_USAGE.map((item, i) => (
                <tr key={i} className="border-b border-cosmic-border last:border-0 hover:bg-cosmic-subtle transition-colors">
                  <td className="px-5 py-3 text-text-accent-cyan font-medium">{item.model}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${item.type === "图片" ? "bg-accent-violet/10 text-accent-violet" : "bg-amber-500/10 text-amber-600"}`}>{item.type}</span>
                  </td>
                  <td className="px-5 py-3 text-text-secondary">{item.quality}</td>
                  <td className="px-5 py-3 text-right text-text-accent-cyan font-mono">{item.credits}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-text-secondary text-center mt-3 flex items-center justify-center gap-1">
          <Info className="w-3 h-3" />生成前始终显示精确 Credits 成本；实际消耗随模型与时长浮动
        </p>
      </motion.div>

      {/* FAQ */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="max-w-2xl mx-auto">
        <h2 className="text-xl font-bold mb-6 text-center text-text-accent-cyan">常见问题</h2>
        <div className="space-y-3">
          {FAQS.map((faq, i) => (
            <div key={i} className="border border-cosmic-border rounded-xl overflow-hidden hover:border-cosmic-border-hover transition-colors">
              <button onClick={() => setOpenFaq(openFaq === i ? null : i)} aria-expanded={openFaq === i}
                className="flex items-center justify-between w-full px-5 py-4 text-left text-sm font-semibold text-text-accent-cyan hover:bg-cosmic-subtle transition-colors">
                <span>{faq.q}</span>
                <ChevronDown className={`w-4 h-4 text-text-secondary transition-transform ${openFaq === i ? "rotate-180" : ""}`} />
              </button>
              {openFaq === i && <div className="px-5 pb-4 text-sm text-text-secondary border-t border-cosmic-border pt-3">{faq.a}</div>}
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
