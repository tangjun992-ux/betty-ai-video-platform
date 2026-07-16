"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/lib/stores";
import { API_BASE } from "@/lib/api";
import { Loading } from "@/components/StatusStates";

/**
 * OIDC / SSO callback — stores JWT from query and hydrates user profile.
 * Backend redirects here as /auth/callback?token=...
 */
function AuthCallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { setToken, setUser } = useAuthStore();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setError("缺少登录令牌");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        setToken(token);
        const r = await fetch(`${API_BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok) throw new Error("无法加载用户资料");
        const me = await r.json();
        if (cancelled) return;
        setUser({
          id: me.id,
          email: me.email,
          name: me.display_name || me.username || me.email,
          role: me.role,
        } as any);
        router.replace("/dashboard");
      } catch (e: any) {
        if (!cancelled) setError(e?.message || "SSO 登录失败");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params, router, setToken, setUser]);

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-4">
        <p className="text-sm text-red-400">{error}</p>
        <a href="/auth/login" className="text-sm text-brand hover:underline">
          返回登录
        </a>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <Loading />
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <Loading />
        </div>
      }
    >
      <AuthCallbackInner />
    </Suspense>
  );
}
