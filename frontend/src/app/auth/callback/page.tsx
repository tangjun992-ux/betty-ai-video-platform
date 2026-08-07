"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/lib/stores";
import { API_BASE, oidcExchange } from "@/lib/api";
import { Loading } from "@/components/StatusStates";

/**
 * OIDC / SSO callback — exchanges one-time code for JWT (Phase 8 secure flow).
 * Legacy `?token=` still supported for dev/back-compat.
 */
function AuthCallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { setToken, setUser } = useAuthStore();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const idpError = params.get("error");
    const idpDesc = params.get("error_description");
    if (idpError) {
      setError(idpDesc || idpError || "IdP 拒绝了登录请求");
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        let token = params.get("token");
        const code = params.get("code");
        if (!token && code) {
          const exchanged = await oidcExchange(code);
          token = exchanged.access_token;
        }
        if (!token) {
          setError("缺少登录凭证（code 或 token）");
          return;
        }
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
