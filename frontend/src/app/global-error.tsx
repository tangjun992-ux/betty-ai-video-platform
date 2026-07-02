"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Inter } from "next/font/google";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
});

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global error:", error);
  }, [error]);

  return (
    <html lang="zh-CN">
      <body
        className={inter.className}
        style={{
          margin: 0,
          background: "#FCFCFE",
          color: "#12121C",
          fontFamily: inter.style.fontFamily,
        }}
      >
        <div
          style={{
            display: "flex",
            minHeight: "100vh",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
          }}
        >
          <div
            style={{
              maxWidth: "28rem",
              width: "100%",
              textAlign: "center",
              background: "#FFFFFF",
              border: "1px solid #E6E6EE",
              borderRadius: "1.25rem",
              padding: "2.5rem 2rem",
              boxShadow:
                "0 12px 28px -6px rgba(18, 18, 28, 0.10), 0 6px 12px -6px rgba(18, 18, 28, 0.06)",
            }}
          >
            {/* Icon */}
            <div
              style={{
                margin: "0 auto 1.5rem",
                width: "4rem",
                height: "4rem",
                borderRadius: "1rem",
                background: "rgba(225, 68, 68, 0.1)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <AlertTriangle
                style={{ width: "2rem", height: "2rem", color: "#E14444" }}
              />
            </div>

            {/* Title */}
            <h1
              style={{
                fontSize: "1.5rem",
                fontWeight: 700,
                marginBottom: "0.5rem",
                color: "#12121C",
              }}
            >
              严重错误
            </h1>

            {/* Description */}
            <p
              style={{
                fontSize: "0.875rem",
                color: "#62626E",
                lineHeight: 1.6,
                marginBottom: "1.5rem",
              }}
            >
              应用遇到了一个严重错误，无法继续运行。请尝试刷新页面重新加载。
            </p>

            {/* Error ID */}
            {error.digest && (
              <p
                style={{
                  fontSize: "0.75rem",
                  color: "#8E8E9C",
                  fontFamily: "monospace",
                  marginBottom: "1.5rem",
                }}
              >
                Error ID: {error.digest}
              </p>
            )}

            {/* Retry button */}
            <button
              onClick={reset}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.625rem 1.5rem",
                borderRadius: "0.75rem",
                background: "#6C5CE7",
                color: "#FFFFFF",
                fontSize: "0.875rem",
                fontWeight: 600,
                border: "none",
                cursor: "pointer",
                boxShadow: "0 8px 24px -6px rgba(108, 92, 231, 0.35)",
              }}
            >
              <RefreshCw style={{ width: "1rem", height: "1rem" }} />
              重新加载
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
