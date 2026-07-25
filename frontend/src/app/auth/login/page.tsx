"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Mail, Lock, Eye, EyeOff, LogIn } from "lucide-react";
import { useAuthStore } from "@/lib/stores";
import { useToast } from "@/components/Toast";
import { login } from "@/lib/api";
import {
  AuthCard,
  AuthField,
  AuthForm,
  AuthSubmitButton,
  PasswordToggle,
} from "@/components/auth/AuthForm";

export default function LoginPage() {
  const router = useRouter();
  const { setUser, setToken } = useAuthStore();
  const toast = useToast();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});

  function validate() {
    const e: typeof errors = {};
    if (!email.trim()) e.email = "请输入邮箱地址";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = "邮箱格式不正确";
    if (!password) e.password = "请输入密码";
    else if (password.length < 6) e.password = "密码至少 6 位";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      const res = await login(email.trim(), password);
      setToken(res.access_token);
      setUser(res.user);
      toast.success("登录成功", `欢迎回来，${res.user.name || res.user.email}`);
      router.push("/dashboard");
    } catch (err: any) {
      toast.error("登录失败", err.message || "请检查邮箱和密码");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      title="欢迎回来"
      subtitle="登录你的 betty 账户继续创作"
      glowSide="left"
      footer={
        <>
          还没有账号？{" "}
          <Link
            href="/auth/register"
            className="text-brand hover:text-brand-strong font-medium transition-colors"
          >
            注册
          </Link>
        </>
      }
    >
      <AuthForm onSubmit={handleSubmit}>
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
          placeholder="输入密码"
          autoComplete="current-password"
          trailing={
            <PasswordToggle
              visible={showPassword}
              onToggle={() => setShowPassword(!showPassword)}
              EyeIcon={Eye}
              EyeOffIcon={EyeOff}
            />
          }
        />

        <AuthSubmitButton loading={loading} icon={LogIn} label="登录" />
      </AuthForm>
    </AuthCard>
  );
}
