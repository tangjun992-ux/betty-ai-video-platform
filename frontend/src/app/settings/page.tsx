"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  User, Sliders, Key, Bell, CreditCard, Info,
  Save, Plus, Trash2, Check, AlertCircle, Loader2,
  Shield, Zap, Mail, Smartphone, Palette, Globe,
  Image, Video, Bot, Eye, EyeOff, Copy, ExternalLink,
} from "lucide-react";
import { useAuthStore } from "@/lib/stores";
import { cn, formatDate, formatCredits } from "@/lib/utils";
import type {
  SettingsResponse, UserPreferences, NotificationSettings,
  ApiKeyInfo, BillingInfo, SettingsProfile, SaveSettingsRequest,
} from "@/lib/api";
import {
  getSettings, saveSettings, createApiKey, deleteApiKey,
} from "@/lib/api";

// ─── Section Definitions ────────────────────────────────

interface Section {
  id: string;
  icon: React.ElementType;
  label: string;
  description?: string;
}

const SECTIONS: Section[] = [
  { id: "account", icon: User, label: "账户", description: "个人信息与安全" },
  { id: "preferences", icon: Sliders, label: "偏好设置", description: "默认模型与创作偏好" },
  { id: "api-keys", icon: Key, label: "API 密钥", description: "管理第三方 API 密钥" },
  { id: "notifications", icon: Bell, label: "通知", description: "邮件与推送通知" },
  { id: "billing", icon: CreditCard, label: "计费", description: "积分余额与使用记录" },
  { id: "about", icon: Info, label: "关于", description: "版本与法律信息" },
];

// ─── Shared Components ──────────────────────────────────

function SectionCard({ title, description, children, className }: {
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("rounded-xl border border-cosmic-border/50 bg-card/50 backdrop-blur-sm p-6", className)}>
      <div className="mb-5">
        <h3 className="text-lg font-semibold">{title}</h3>
        {description && (
          <p className="text-sm text-text-secondary mt-0.5">{description}</p>
        )}
      </div>
      {children}
    </div>
  );
}

function SaveButton({ onClick, loading, label = "保存" }: {
  onClick: () => void;
  loading?: boolean;
  label?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={cn(
        "inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200",
        "bg-accent-cyan text-white hover:bg-accent-cyan/80 active:scale-95",
        "disabled:opacity-50 disabled:cursor-not-allowed"
      )}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <Save className="w-4 h-4" />
      )}
      {loading ? "保存中..." : label}
    </button>
  );
}

function ToggleRow({ label, description, checked, onChange }: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-cosmic-border/40 last:border-0">
      <div className="flex-1 mr-4">
        <p className="text-sm font-medium">{label}</p>
        {description && (
          <p className="text-xs text-text-secondary mt-0.5">{description}</p>
        )}
      </div>
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200",
          checked ? "bg-accent-cyan" : "bg-text-secondary/30"
        )}
      >
        <span
          className={cn(
            "inline-block h-4 w-4 rounded-full bg-white transition-transform duration-200",
            checked ? "translate-x-6" : "translate-x-1"
          )}
        />
      </button>
    </div>
  );
}

function SelectField({ label, value, options, onChange, className }: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-between py-3 border-b border-cosmic-border/40 last:border-0", className)}>
      <span className="text-sm font-medium">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 px-3 rounded-lg bg-cosmic-surface/50 border border-cosmic-border/50 text-sm text-text-accent-cyan focus:outline-none focus:ring-2 focus:ring-accent-cyan/20 focus:border-accent-cyan/30 transition-all"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  );
}

function InputField({ label, value, placeholder, onChange, type = "text", className }: {
  label: string;
  value: string;
  placeholder?: string;
  onChange: (v: string) => void;
  type?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-between py-3 border-b border-cosmic-border/40 last:border-0", className)}>
      <span className="text-sm font-medium shrink-0 mr-4">{label}</span>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 px-3 rounded-lg bg-cosmic-surface/50 border border-cosmic-border/50 text-sm text-text-accent-cyan placeholder:text-text-secondary/50 focus:outline-none focus:ring-2 focus:ring-accent-cyan/20 focus:border-accent-cyan/30 transition-all min-w-0 w-48"
      />
    </div>
  );
}

// ─── Account Section ────────────────────────────────────

function AccountSection({ profile, onUpdate, saving }: {
  profile: SettingsProfile;
  onUpdate: (data: SaveSettingsRequest) => Promise<void>;
  saving: boolean;
}) {
  const [displayName, setDisplayName] = useState(profile.display_name || "");
  const [email, setEmail] = useState(profile.email || "");
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    setSaved(false);
    await onUpdate({
      profile: {
        display_name: displayName || undefined,
        email: email || undefined,
      },
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <SectionCard title="个人信息" description="管理你的账户信息">
      <div className="space-y-1">
        <div className="flex items-center justify-between py-3 border-b border-cosmic-border/40">
          <span className="text-sm font-medium">用户名</span>
          <span className="text-sm text-text-secondary">{profile.username}</span>
        </div>
        <InputField label="显示名称" value={displayName} placeholder="输入名称" onChange={setDisplayName} />
        <InputField label="邮箱" value={email} placeholder="your@email.com" onChange={setEmail} type="email" />
        <div className="flex items-center justify-between py-3 border-b border-cosmic-border/40">
          <span className="text-sm font-medium">账户角色</span>
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-accent-cyan/[0.08] text-accent-cyan">
            <Shield className="w-3 h-3" />
            {profile.role === "enterprise" ? "企业版" : profile.role === "pro" ? "专业版" : profile.role === "creator" ? "创作者" : "免费版"}
          </span>
        </div>
      </div>
      <div className="mt-5 flex items-center gap-3">
        <SaveButton onClick={handleSave} loading={saving} />
        {saved && (
          <span className="inline-flex items-center gap-1 text-sm text-green-400">
            <Check className="w-4 h-4" /> 已保存
          </span>
        )}
      </div>
    </SectionCard>
  );
}

// ─── Preferences Section ────────────────────────────────

function PreferencesSection({
  preferences,
  onUpdate,
  saving,
}: {
  preferences: UserPreferences;
  onUpdate: (data: SaveSettingsRequest) => Promise<void>;
  saving: boolean;
}) {
  const [prefs, setPrefs] = useState(preferences);
  const [saved, setSaved] = useState(false);

  useEffect(() => setPrefs(preferences), [preferences]);

  const update = (key: keyof UserPreferences, value: string | boolean) => {
    setPrefs((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaved(false);
    await onUpdate({ preferences: prefs });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const qualityOpts = [
    { value: "fast", label: "快速" },
    { value: "balanced", label: "均衡" },
    { value: "high", label: "高质量" },
  ];
  const langOpts = [
    { value: "zh-CN", label: "简体中文" },
    { value: "en", label: "English" },
    { value: "ja", label: "日本語" },
  ];
  const themeOpts = [
    { value: "dark", label: "暗色" },
    { value: "light", label: "亮色" },
  ];
  const resOpts = [
    { value: "512x512", label: "512×512" },
    { value: "1024x1024", label: "1024×1024" },
    { value: "1080x1080", label: "1080×1080" },
    { value: "1920x1080", label: "1920×1080 (16:9)" },
  ];

  return (
    <SectionCard title="创作偏好" description="设置默认的生成参数">
      <div className="space-y-1">
        <InputField
          label="默认模型"
          value={prefs.default_model}
          placeholder="auto"
          onChange={(v) => update("default_model", v)}
        />
        <SelectField label="默认质量" value={prefs.default_quality} options={qualityOpts} onChange={(v) => update("default_quality", v)} />
        <SelectField label="默认分辨率" value={prefs.default_resolution} options={resOpts} onChange={(v) => update("default_resolution", v)} />
        <SelectField label="语言" value={prefs.language} options={langOpts} onChange={(v) => update("language", v)} />
        <SelectField label="主题" value={prefs.theme} options={themeOpts} onChange={(v) => update("theme", v)} />
        <ToggleRow
          label="自动优化 Prompt"
          description="生成前自动增强指令描述"
          checked={prefs.auto_enhance_prompt}
          onChange={(v) => update("auto_enhance_prompt", v)}
        />
        <ToggleRow
          label="保存创作历史"
          description="在本地和云端保存你的生成记录"
          checked={prefs.save_history}
          onChange={(v) => update("save_history", v)}
        />
      </div>
      <div className="mt-5 flex items-center gap-3">
        <SaveButton onClick={handleSave} loading={saving} />
        {saved && (
          <span className="inline-flex items-center gap-1 text-sm text-green-400">
            <Check className="w-4 h-4" /> 已保存
          </span>
        )}
      </div>
    </SectionCard>
  );
}

// ─── API Keys Section ───────────────────────────────────

function ApiKeysSection({
  apiKeys,
  onAdd,
  onDelete,
  loading,
}: {
  apiKeys: ApiKeyInfo[];
  onAdd: (name: string, provider: string, key: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  loading?: boolean;
}) {
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newProvider, setNewProvider] = useState("custom");
  const [newKey, setNewKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [adding, setAdding] = useState(false);

  const handleAdd = async () => {
    if (!newName || !newKey) return;
    setAdding(true);
    try {
      await onAdd(newName, newProvider, newKey);
      setShowAdd(false);
      setNewName("");
      setNewKey("");
      setNewProvider("custom");
    } finally {
      setAdding(false);
    }
  };

  return (
    <SectionCard title="API 密钥" description="管理第三方模型 API 密钥">
      {apiKeys.length === 0 && !showAdd ? (
        <div className="py-8 text-center">
          <Key className="w-10 h-10 mx-auto mb-3 text-text-secondary/40" />
          <p className="text-sm text-text-secondary">暂无 API 密钥</p>
          <p className="text-xs text-text-secondary/60 mt-1">
            添加你自己的 API 密钥以使用更多模型
          </p>
          <button
            onClick={() => setShowAdd(true)}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-cyan/[0.08] text-accent-cyan text-sm font-medium hover:bg-accent-cyan/[0.12] transition-all"
          >
            <Plus className="w-4 h-4" /> 添加密钥
          </button>
        </div>
      ) : (
        <>
          <div className="space-y-2">
            {apiKeys.map((key) => (
              <div
                key={key.id}
                className="flex items-center justify-between py-3 px-4 rounded-lg bg-cosmic-surface/30 border border-cosmic-border/40"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium truncate">{key.name}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-cosmic-surface text-text-secondary">
                      {key.provider}
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary font-mono mt-0.5">
                    {key.key_preview}
                  </p>
                </div>
                <button
                  onClick={() => onDelete(key.id)}
                  className="p-2 rounded-lg hover:bg-destructive/10 text-text-secondary hover:text-destructive transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          {showAdd ? (
            <div className="mt-4 p-4 rounded-xl border border-cosmic-border/50 bg-cosmic-surface/20 space-y-3">
              <h4 className="text-sm font-medium">添加新密钥</h4>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="密钥名称 (如: 我的 OpenAI)"
                className="w-full h-9 px-3 rounded-lg bg-cosmic-surface/50 border border-cosmic-border/50 text-sm text-text-accent-cyan placeholder:text-text-secondary/50 focus:outline-none focus:ring-2 focus:ring-accent-cyan/20"
              />
              <select
                value={newProvider}
                onChange={(e) => setNewProvider(e.target.value)}
                className="w-full h-9 px-3 rounded-lg bg-cosmic-surface/50 border border-cosmic-border/50 text-sm text-text-accent-cyan focus:outline-none focus:ring-2 focus:ring-accent-cyan/20"
              >
                <option value="custom">自定义</option>
                <option value="openai">OpenAI</option>
                <option value="kie">KIE.ai</option>
                <option value="seedance">Seedance</option>
                <option value="kling">Kling</option>
              </select>
              <div className="relative">
                <input
                  type={showKey ? "text" : "password"}
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  placeholder="sk-..."
                  className="w-full h-9 px-3 pr-10 rounded-lg bg-cosmic-surface/50 border border-cosmic-border/50 text-sm text-text-accent-cyan placeholder:text-text-secondary/50 focus:outline-none focus:ring-2 focus:ring-accent-cyan/20"
                />
                <button
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-text-secondary hover:text-text-accent-cyan"
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleAdd}
                  disabled={adding || !newName || !newKey}
                  className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-accent-cyan text-white text-sm font-medium hover:bg-accent-cyan/80 disabled:opacity-50 transition-all"
                >
                  {adding ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  {adding ? "添加中..." : "添加"}
                </button>
                <button
                  onClick={() => { setShowAdd(false); setNewName(""); setNewKey(""); }}
                  className="px-4 py-2 rounded-xl bg-cosmic-surface text-sm text-text-secondary hover:text-text-accent-cyan transition-all"
                >
                  取消
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowAdd(true)}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cosmic-surface/50 text-sm text-text-secondary hover:text-text-accent-cyan hover:bg-cosmic-surface transition-all"
            >
              <Plus className="w-4 h-4" /> 添加密钥
            </button>
          )}
        </>
      )}
    </SectionCard>
  );
}

// ─── Notifications Section ──────────────────────────────

function NotificationsSection({
  notifications,
  onUpdate,
  saving,
}: {
  notifications: NotificationSettings;
  onUpdate: (data: SaveSettingsRequest) => Promise<void>;
  saving: boolean;
}) {
  const [notifs, setNotifs] = useState(notifications);
  const [saved, setSaved] = useState(false);

  useEffect(() => setNotifs(notifications), [notifications]);

  const update = (key: keyof NotificationSettings, value: boolean) => {
    setNotifs((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaved(false);
    await onUpdate({ notifications: notifs });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-4">
      <SectionCard title="邮件通知" description="通过邮件接收重要更新">
        <div className="space-y-0">
          <ToggleRow
            label="任务完成通知"
            description="生成任务完成后发送邮件"
            checked={notifs.email_task_complete}
            onChange={(v) => update("email_task_complete", v)}
          />
          <ToggleRow
            label="每周摘要"
            description="每周创作统计报告"
            checked={notifs.email_weekly_digest}
            onChange={(v) => update("email_weekly_digest", v)}
          />
          <ToggleRow
            label="促销与更新"
            description="产品更新和优惠活动"
            checked={notifs.email_promotions}
            onChange={(v) => update("email_promotions", v)}
          />
        </div>
      </SectionCard>

      <SectionCard title="推送通知" description="浏览器和应用内推送">
        <div className="space-y-0">
          <ToggleRow
            label="任务完成推送"
            description="生成完成后实时推送"
            checked={notifs.push_task_complete}
            onChange={(v) => update("push_task_complete", v)}
          />
          <ToggleRow
            label="积分不足提醒"
            description="积分余额低于阈值时提醒"
            checked={notifs.push_credits_low}
            onChange={(v) => update("push_credits_low", v)}
          />
        </div>
      </SectionCard>

      <div className="flex items-center gap-3">
        <SaveButton onClick={handleSave} loading={saving} />
        {saved && (
          <span className="inline-flex items-center gap-1 text-sm text-green-400">
            <Check className="w-4 h-4" /> 已保存
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Billing Section ────────────────────────────────────

function BillingSection({ billing }: { billing: BillingInfo }) {
  const planLabels: Record<string, string> = {
    free: "免费版", creator: "创作者", pro: "专业版", enterprise: "企业版",
  };

  const tnxLabels: Record<string, string> = {
    purchase: "购买积分", consumption: "任务消耗", refund: "退款",
    bonus: "系统赠送", daily_free: "每日免费",
  };

  return (
    <div className="space-y-4">
      {/* Plan & Credits */}
      <SectionCard title="当前套餐">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-cosmic-surface/30 border border-cosmic-border/40">
            <p className="text-xs text-text-secondary mb-1">套餐</p>
            <p className="text-lg font-bold text-accent-cyan">
              {planLabels[billing.plan] || billing.plan}
            </p>
          </div>
          <div className="p-4 rounded-xl bg-cosmic-surface/30 border border-cosmic-border/40">
            <p className="text-xs text-text-secondary mb-1">积分余额</p>
            <p className="text-lg font-bold">{formatCredits(billing.credits)}</p>
          </div>
          <div className="p-4 rounded-xl bg-cosmic-surface/30 border border-cosmic-border/40">
            <p className="text-xs text-text-secondary mb-1">每日免费</p>
            <p className="text-lg font-bold">
              {billing.daily_credits}/{billing.daily_credits_max}
            </p>
          </div>
          <div className="p-4 rounded-xl bg-cosmic-surface/30 border border-cosmic-border/40">
            <p className="text-xs text-text-secondary mb-1">已完成任务</p>
            <p className="text-lg font-bold">{billing.total_tasks}</p>
          </div>
        </div>
        <div className="mt-4 flex gap-3">
          <a
            href="/pricing"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-cyan/[0.08] text-accent-cyan text-sm font-medium hover:bg-accent-cyan/[0.12] transition-all"
          >
            <Zap className="w-4 h-4" /> 升级套餐
          </a>
        </div>
      </SectionCard>

      {/* Transactions */}
      <SectionCard title="最近交易" description="积分变动记录">
        {billing.recent_transactions.length === 0 ? (
          <p className="text-sm text-text-secondary py-4 text-center">暂无交易记录</p>
        ) : (
          <div className="space-y-1">
            {billing.recent_transactions.map((txn) => (
              <div
                key={txn.id}
                className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-cosmic-surface/20 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate">
                    {txn.description || tnxLabels[txn.type] || txn.type}
                  </p>
                  <p className="text-xs text-text-secondary">
                    {txn.created_at ? formatDate(txn.created_at) : ""}
                  </p>
                </div>
                <span
                  className={cn(
                    "text-sm font-mono font-medium",
                    txn.amount > 0 ? "text-green-400" : "text-destructive"
                  )}
                >
                  {txn.amount > 0 ? "+" : ""}{txn.amount}
                </span>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}

// ─── About Section ──────────────────────────────────────

function AboutSection() {
  return (
    <SectionCard title="关于 betty">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl overflow-hidden">
            <img src="/brand/logo-icon.png" alt="betty" className="w-full h-full object-cover" />
          </div>
          <div>
            <h4 className="font-semibold text-lg">betty</h4>
            <p className="text-sm text-text-secondary">AI 内容创作平台</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-lg bg-cosmic-surface/30 border border-cosmic-border/40">
            <p className="text-xs text-text-secondary">版本</p>
            <p className="text-sm font-medium font-mono">v0.1.0</p>
          </div>
          <div className="p-3 rounded-lg bg-cosmic-surface/30 border border-cosmic-border/40">
            <p className="text-xs text-text-secondary">环境</p>
            <p className="text-sm font-medium">Development</p>
          </div>
          <div className="p-3 rounded-lg bg-cosmic-surface/30 border border-cosmic-border/40">
            <p className="text-xs text-text-secondary">技术栈</p>
            <p className="text-sm font-medium">Next.js + FastAPI</p>
          </div>
          <div className="p-3 rounded-lg bg-cosmic-surface/30 border border-cosmic-border/40">
            <p className="text-xs text-text-secondary">支持模型</p>
            <p className="text-sm font-medium">GPT Image · Seedance · Kling</p>
          </div>
        </div>

        <div className="flex flex-col gap-2 pt-2">
          <a href="#" className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-accent-cyan transition-colors">
            <ExternalLink className="w-4 h-4" /> 服务条款
          </a>
          <a href="#" className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-accent-cyan transition-colors">
            <ExternalLink className="w-4 h-4" /> 隐私政策
          </a>
          <a href="#" className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-accent-cyan transition-colors">
            <ExternalLink className="w-4 h-4" /> 帮助文档
          </a>
        </div>
      </div>
    </SectionCard>
  );
}

// ─── Sidebar Navigation ─────────────────────────────────

function SettingsSidebar({
  activeSection,
  onSelect,
}: {
  activeSection: string;
  onSelect: (id: string) => void;
}) {
  return (
    <nav className="w-full md:w-56 shrink-0 space-y-1">
      {SECTIONS.map((section) => (
        <button
          key={section.id}
          onClick={() => onSelect(section.id)}
          className={cn(
            "flex items-center gap-3 w-full px-4 py-2.5 rounded-lg text-sm transition-all duration-200 text-left",
            activeSection === section.id
              ? "bg-accent-cyan/[0.08] text-accent-cyan font-medium"
              : "text-text-secondary hover:text-text-accent-cyan hover:bg-cosmic-surface/30"
          )}
        >
          <section.icon className={cn("w-4 h-4", activeSection === section.id && "text-accent-cyan")} />
          <div className="flex-1 min-w-0">
            <span>{section.label}</span>
            {section.description && (
              <p className="text-xs text-text-secondary/60 truncate">{section.description}</p>
            )}
          </div>
        </button>
      ))}
    </nav>
  );
}

// ─── Main Settings Page ─────────────────────────────────

export default function SettingsPage() {
  const { user, token } = useAuthStore();
  const [activeSection, setActiveSection] = useState("account");
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      setError(null);
      const data = await getSettings(token);
      setSettings(data);
    } catch (err: any) {
      setError(err.message || "加载设置失败");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const handleSaveSettings = async (data: SaveSettingsRequest) => {
    if (!token) return;
    setSaving(true);
    try {
      await saveSettings(token, data);
      // Reload settings to get fresh state
      await loadSettings();
    } catch (err: any) {
      setError(err.message || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleAddApiKey = async (name: string, provider: string, key: string) => {
    if (!token) return;
    await createApiKey(token, { name, provider, key });
    await loadSettings();
  };

  const handleDeleteApiKey = async (keyId: string) => {
    if (!token) return;
    await deleteApiKey(token, keyId);
    await loadSettings();
  };

  // Not logged in
  if (!token || !user) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="text-center py-20">
          <User className="w-16 h-16 mx-auto mb-4 text-text-secondary/30" />
          <h2 className="text-xl font-semibold mb-2">请先登录</h2>
          <p className="text-text-secondary mb-6">登录后即可管理你的账户设置</p>
          <a
            href="/login"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-accent-cyan text-white font-medium hover:bg-accent-cyan/80 transition-all"
          >
            前往登录
          </a>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-accent-cyan" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 md:py-12">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">设置</h1>
        <p className="text-sm text-text-secondary mt-1">
          管理你的账户、偏好和 API 密钥
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-destructive/10 border border-destructive/30 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-destructive shrink-0" />
          <p className="text-sm text-destructive">{error}</p>
          <button
            onClick={() => setError(null)}
            className="ml-auto p-1 text-destructive/60 hover:text-destructive"
          >
            ×
          </button>
        </div>
      )}

      {/* Layout: Mobile vertical | Desktop horizontal */}
      <div className="flex flex-col md:flex-row gap-6 md:gap-8">
        {/* Sidebar */}
        <SettingsSidebar activeSection={activeSection} onSelect={setActiveSection} />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeSection}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.15 }}
            >
              {activeSection === "account" && settings && (
                <AccountSection
                  profile={settings.profile}
                  onUpdate={handleSaveSettings}
                  saving={saving}
                />
              )}
              {activeSection === "preferences" && settings && (
                <PreferencesSection
                  preferences={settings.preferences}
                  onUpdate={handleSaveSettings}
                  saving={saving}
                />
              )}
              {activeSection === "api-keys" && settings && (
                <ApiKeysSection
                  apiKeys={settings.api_keys}
                  onAdd={handleAddApiKey}
                  onDelete={handleDeleteApiKey}
                  loading={saving}
                />
              )}
              {activeSection === "notifications" && settings && (
                <NotificationsSection
                  notifications={settings.notifications}
                  onUpdate={handleSaveSettings}
                  saving={saving}
                />
              )}
              {activeSection === "billing" && settings && (
                <BillingSection billing={settings.billing} />
              )}
              {activeSection === "about" && <AboutSection />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
