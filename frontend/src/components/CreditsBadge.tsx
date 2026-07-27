"use client";

import { useEffect, useState } from "react";

import { API_BASE } from "@/lib/api";

export function CreditsBadge() {
  const [balance, setBalance] = useState<number | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/models/pricing/user`)
      .then((r) => r.json())
      .then((data) => {
        if (data.credits !== undefined) {
          setBalance(data.credits);
        }
      })
      .catch(() => setError(true));
  }, []);

  if (error || balance === null) return null;

  return (
    <a
      href="/pricing"
      className="flex items-center gap-1.5 px-3 py-1.5 bg-dark-800 rounded-full text-xs hover:bg-dark-700 transition border border-dark-700"
    >
      <span className="text-yellow-400">⚡</span>
      <span className="text-dark-300 font-medium">{balance.toLocaleString()}</span>
    </a>
  );
}
