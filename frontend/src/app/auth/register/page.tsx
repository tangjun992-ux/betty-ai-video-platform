"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Mail, Lock, User, Eye, EyeOff, UserPlus } from "lucide-react";
import { useAuthStore, useOnboardingStore } from "@/lib/stores";
import { useToast } from "@/components/Toast";
import { register, trackOnboarding } from "@/lib/api";
import {
  AuthCard,
  AuthField,
  AuthForm,
  AuthSubmitButton,
  PasswordToggle,
} from "@/components/auth/AuthForm";

export default function RegisterPage() {
  const router = useRouter();
  const { setUser, setToken } = useAuthStore();
  const startOnboarding = useOnboardingStore((s) => s.startFor);
  const toast = useToast();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{
    username?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
  }>({});

  function validate() {
    const e: typeof errors = {};
    if (!username.trim()) e.username = "请输入用户名";
    else if (username.trim().length < 2) e.username = "用户名至少 2 个字符";
    if (!email.trim()) e.email = "请输入邮箱地址";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = "邮箱格式不正确";
    if (!password) e.password = "请输入密码";
    else if (password.length < 6) e.password = "密码至少 6 位";
    if (!confirmPassword) e.confirmPassword = "请确认密码";
    else if (password !== confirmPassword) e.confirmPassword = "两次密码不一致";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      const res = await register(username.trim(), email.trim(), password);
      setToken(res.access_token);
      setUser(res.user);
      startOnboarding(String(res.user.id));
      trackOnboarding("started");
      toast.success("注册成功", `欢迎加入 betty，${res.user.name || username}`);
      const firstPrompt = "一杯精品咖啡放在大理石桌面，清晨柔光，商业产品摄影，电影级质感";
      router.push(`/create/image?onboard=1&prompt=${encodeURIComponent(firstPrompt)}`);
    } catch (err: any) {
      toast.error("注册失败", err.message || "请稍后重试");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      title="创建账户"
      subtitle="开始你的 AI 创作之旅"
      glowSide="right"
      footer={
        <>
          已有账号？{" "}
          <Link
            href="/auth/login"
            className="text-brand hover:text-brand-strong font-medium transition-colors"
          >
            登录
          </Link>
        </>
      }
    >
      <AuthForm onSubmit={handleSubmit} spacing="space-y-4">
        <AuthField
          label="用户名"
          icon={User}
          error={errors.username}
          type="text"
          value={username}
          onChange={(e) => {
            setUsername(e.target.value);
            if (errors.username) setErrors((p) => ({ ...p, username: undefined }));
          }}
          placeholder="你的用户名"
          autoComplete="username"
        />

        <AuthField
          label="邮箱地址"
          icon={Mail}
          error={errors.email}
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (errors.email) setErrors((p) => ({ ...p, email: undefined }));
          }}
          placeholder="your@email.com"
          autoComplete="email"
        />

        <AuthField
          label="密码"
          icon={Lock}
          error={errors.password}
          className="pr-10"
          type={showPassword ? "text" : "password"}
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (errors.password) setErrors((p) => ({ ...p, password: undefined }));
          }}
          placeholder="至少 6 位密码"
          autoComplete="new-password"
          trailing={
            <PasswordToggle
              visible={showPassword}
              onToggle={() => setShowPassword(!showPassword)}
              EyeIcon={Eye}
              EyeOffIcon={EyeOff}
            />
          }
        />

        <AuthField
          label="确认密码"
          icon={Lock}
          error={errors.confirmPassword}
          type={showPassword ? "text" : "password"}
          value={confirmPassword}
          onChange={(e) => {
            setConfirmPassword(e.target.value);
            if (errors.confirmPassword) setErrors((p) => ({ ...p, confirmPassword: undefined }));
          }}
          placeholder="再次输入密码"
          autoComplete="new-password"
        />

        <AuthSubmitButton loading={loading} icon={UserPlus} label="注册" className="mt-2" />
      </AuthForm>
    </AuthCard>
  );
}
