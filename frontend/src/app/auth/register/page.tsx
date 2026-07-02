"use client";

import { useState, type FormEvent } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Mail, Lock, User, Eye, EyeOff, UserPlus, Sparkles } from "lucide-react";
import { useAuthStore } from "@/lib/stores";
import { useToast } from "@/components/Toast";
import { register } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const { setUser, setToken } = useAuthStore();
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
      toast.success("注册成功", `欢迎加入 betty，${res.user.name || username}`);
      router.push("/dashboard");
    } catch (err: any) {
      toast.error("注册失败", err.message || "请稍后重试");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-accent-cyan/[0.04] rounded-full blur-[120px]" />
        <div className="absolute bottom-0 left-1/4 w-[400px] h-[400px] bg-violet-500/[0.04] rounded-full blur-[100px]" />
        <div
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage:
              "linear-gradient(hsl(var(--primary)/0.5) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--primary)/0.5) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
            maskImage:
              "radial-gradient(ellipse 60% 50% at 50% 50%, black 30%, transparent 70%)",
          }}
        />
      </div>

      {/* Card */}
      <motion.div
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-md"
      >
        <div className="glass-card shadow-elevation-lg p-8 md:p-10">
          {/* Logo + Title */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-center mb-8"
          >
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-accent-violet to-accent-cyan mb-4 shadow-button-glow">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-text-primary mb-1">创建账户</h1>
            <p className="text-sm text-text-secondary">开始你的 AI 创作之旅</p>
          </motion.div>

          {/* Form */}
          <motion.form
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            onSubmit={handleSubmit}
            className="space-y-4"
          >
            {/* Username */}
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1.5">
                用户名
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary/50" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => {
                    setUsername(e.target.value);
                    if (errors.username) setErrors((p) => ({ ...p, username: undefined }));
                  }}
                  placeholder="你的用户名"
                  className="input-primary pl-10"
                  autoComplete="username"
                />
              </div>
              {errors.username && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-xs text-destructive mt-1.5"
                >
                  {errors.username}
                </motion.p>
              )}
            </div>

            {/* Email */}
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1.5">
                邮箱地址
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary/50" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (errors.email) setErrors((p) => ({ ...p, email: undefined }));
                  }}
                  placeholder="your@email.com"
                  className="input-primary pl-10"
                  autoComplete="email"
                />
              </div>
              {errors.email && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-xs text-destructive mt-1.5"
                >
                  {errors.email}
                </motion.p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1.5">
                密码
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary/50" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (errors.password) setErrors((p) => ({ ...p, password: undefined }));
                  }}
                  placeholder="至少 6 位密码"
                  className="input-primary pl-10 pr-10"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-text-secondary/50 hover:text-text-secondary transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-xs text-destructive mt-1.5"
                >
                  {errors.password}
                </motion.p>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1.5">
                确认密码
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary/50" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    if (errors.confirmPassword)
                      setErrors((p) => ({ ...p, confirmPassword: undefined }));
                  }}
                  placeholder="再次输入密码"
                  className="input-primary pl-10"
                  autoComplete="new-password"
                />
              </div>
              {errors.confirmPassword && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-xs text-destructive mt-1.5"
                >
                  {errors.confirmPassword}
                </motion.p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full h-11 text-base mt-2"
            >
              {loading ? (
                <motion.span
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                  className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                />
              ) : (
                <>
                  <UserPlus className="w-4 h-4" />
                  注册
                </>
              )}
            </button>
          </motion.form>

          {/* Footer Link */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-center text-sm text-text-secondary mt-6"
          >
            已有账号？{" "}
            <Link
              href="/auth/login"
              className="text-accent-cyan hover:text-accent-cyan-hover font-medium transition-colors"
            >
              登录
            </Link>
          </motion.p>
        </div>
      </motion.div>
    </div>
  );
}
