"use client";

import { type ComponentType, type FormEvent, type InputHTMLAttributes, type ReactNode } from "react";
import { motion } from "framer-motion";
import { BrandMark } from "@/components/BrandLogo";

type GlowSide = "left" | "right";

export function AuthCard({
  title,
  subtitle,
  glowSide = "left",
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  glowSide?: GlowSide;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className={`absolute top-0 ${glowSide === "left" ? "left-1/4" : "right-1/4"} w-[500px] h-[500px] bg-accent-cyan/[0.04] rounded-full blur-[120px]`}
        />
        <div
          className={`absolute bottom-0 ${glowSide === "left" ? "right-1/4" : "left-1/4"} w-[400px] h-[400px] bg-violet-500/[0.04] rounded-full blur-[100px]`}
        />
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

      <motion.div
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-md"
      >
        <div className="glass-card shadow-elevation-lg p-8 md:p-10">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-center mb-8"
          >
            <BrandMark className="w-14 h-14 mx-auto mb-4 shadow-button-glow rounded-2xl" />
            <h1 className="text-2xl font-bold text-text-primary mb-1">{title}</h1>
            <p className="text-sm text-text-secondary">{subtitle}</p>
          </motion.div>

          {children}

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-center text-sm text-text-secondary mt-6"
          >
            {footer}
          </motion.p>
        </div>
      </motion.div>
    </div>
  );
}

export function AuthForm({
  onSubmit,
  spacing = "space-y-5",
  children,
}: {
  onSubmit: (e: FormEvent) => void;
  spacing?: string;
  children: ReactNode;
}) {
  return (
    <motion.form
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2 }}
      onSubmit={onSubmit}
      className={spacing}
    >
      {children}
    </motion.form>
  );
}

export function AuthField({
  label,
  icon: Icon,
  error,
  trailing,
  className = "",
  ...inputProps
}: {
  label: string;
  icon: ComponentType<{ className?: string }>;
  error?: string;
  trailing?: ReactNode;
} & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div>
      <label className="block text-xs font-medium text-text-secondary mb-1.5">{label}</label>
      <div className="relative">
        <Icon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary/50" />
        <input className={`input-primary pl-10 ${className}`} {...inputProps} />
        {trailing}
      </div>
      {error && (
        <motion.p
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-xs text-destructive mt-1.5"
        >
          {error}
        </motion.p>
      )}
    </div>
  );
}

export function PasswordToggle({
  visible,
  onToggle,
  EyeIcon,
  EyeOffIcon,
}: {
  visible: boolean;
  onToggle: () => void;
  EyeIcon: ComponentType<{ className?: string }>;
  EyeOffIcon: ComponentType<{ className?: string }>;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-text-secondary/50 hover:text-text-secondary transition-colors"
    >
      {visible ? <EyeOffIcon className="w-4 h-4" /> : <EyeIcon className="w-4 h-4" />}
    </button>
  );
}

export function AuthSubmitButton({
  loading,
  icon: Icon,
  label,
  className = "",
}: {
  loading: boolean;
  icon: ComponentType<{ className?: string }>;
  label: string;
  className?: string;
}) {
  return (
    <button type="submit" disabled={loading} className={`btn-primary w-full h-11 text-base ${className}`}>
      {loading ? (
        <motion.span
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
          className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
        />
      ) : (
        <>
          <Icon className="w-4 h-4" />
          {label}
        </>
      )}
    </button>
  );
}
