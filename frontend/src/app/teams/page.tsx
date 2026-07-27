"use client";

import { useEffect, useState, useCallback } from "react";
import { Users, Plus, Loader2, Mail, UserPlus } from "lucide-react";
import { API_BASE, activeTeamId, setActiveTeamId } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

interface TeamMember {
  user_id: number;
  role: string;
  status: string;
  invite_email?: string;
  invite_username?: string;
}
interface Team {
  team_id: string;
  name: string;
  description?: string;
  default_visibility: string;
  seat_limit?: number;
  shared_credits?: number;
  members: TeamMember[];
}

export default function TeamsPage() {
  const toast = useToast();
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [invite, setInvite] = useState<{ teamId: string; value: string } | null>(null);
  const [inviting, setInviting] = useState(false);
  const [billingTeamId, setBillingTeamId] = useState<string | null>(null);
  const [fundAmount, setFundAmount] = useState("500");
  const [funding, setFunding] = useState(false);
  const [buyingSeats, setBuyingSeats] = useState(false);

  useEffect(() => {
    setBillingTeamId(activeTeamId());
  }, []);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/teams/`);
      if (res.status === 401) {
        setTeams([]);
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      setTeams(d.teams || []);
    } catch (e: any) {
      toast.error("加载团队失败", e.message || "");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!name.trim() || creating) return;
    setCreating(true);
    try {
      const res = await fetch(`${API_BASE}/teams/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), default_visibility: "team" }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || `HTTP ${res.status}`);
      }
      setName("");
      toast.success("团队已创建");
      await load();
    } catch (e: any) {
      toast.error("创建失败", e.message || "请先登录");
    } finally {
      setCreating(false);
    }
  };

  const doInvite = async () => {
    if (!invite?.value.trim() || inviting) return;
    setInviting(true);
    try {
      const value = invite.value.trim();
      const body = value.includes("@") ? { email: value } : { username: value };
      const res = await fetch(`${API_BASE}/teams/${invite.teamId}/invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || `HTTP ${res.status}`);
      }
      toast.success("已发送邀请");
      setInvite(null);
      await load();
    } catch (e: any) {
      toast.error("邀请失败", e.message || "");
    } finally {
      setInviting(false);
    }
  };

  const useTeamPool = (teamId: string) => {
    setActiveTeamId(teamId);
    setBillingTeamId(teamId);
    toast.success("已切换扣费来源", "创作时将使用此团队共享池");
  };

  const clearTeamPool = () => {
    setActiveTeamId(null);
    setBillingTeamId(null);
    toast.success("已切换为个人账户扣费");
  };

  const fundTeam = async (teamId: string) => {
    const amount = parseInt(fundAmount, 10);
    if (!amount || amount < 1 || funding) return;
    setFunding(true);
    try {
      const res = await fetch(`${API_BASE}/teams/${teamId}/fund`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || `HTTP ${res.status}`);
      }
      toast.success("充值成功", `已向团队池转入 ${amount} 积分`);
      await load();
    } catch (e: any) {
      toast.error("充值失败", e.message || "");
    } finally {
      setFunding(false);
    }
  };

  const buySeats = async (teamId: string) => {
    if (buyingSeats) return;
    setBuyingSeats(true);
    try {
      const res = await fetch(`${API_BASE}/billing/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: "team_seats",
          id: "seat_monthly",
          team_id: teamId,
          quantity: 1,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
        return;
      }
      toast.success("席位已购买", `+${data.seats_added ?? 1} 席`);
      await load();
    } catch (e: any) {
      toast.error("购买席位失败", e.message || "");
    } finally {
      setBuyingSeats(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <div className="flex items-center gap-3 mb-8">
        <Users className="w-6 h-6 text-brand" />
        <div>
          <h1 className="text-2xl font-display font-bold">团队协作</h1>
          <p className="text-sm text-text-secondary">创建团队、邀请成员，共享项目可见性</p>
        </div>
      </div>

      <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-4 mb-6 flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") create(); }}
          placeholder="新团队名称…"
          className="flex-1 input-cosmic"
        />
        <button onClick={create} disabled={!name.trim() || creating} className="btn-primary">
          {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          创建
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-text-secondary text-center py-12">加载中…</p>
      ) : teams.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-cosmic-border p-10 text-center text-sm text-text-tertiary">
          还没有团队。登录后创建一个，即可邀请协作者。
        </div>
      ) : (
        <div className="space-y-4">
          {teams.map((t) => (
            <div key={t.team_id} className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-5">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <h2 className="font-semibold text-text-primary">{t.name}</h2>
                  {t.description && <p className="text-xs text-text-secondary mt-0.5">{t.description}</p>}
                  <p className="text-[11px] text-text-tertiary mt-1">
                    可见性：{t.default_visibility} · {t.members?.length || 0}/{t.seat_limit ?? 5} 席
                    {typeof t.shared_credits === "number" && (
                      <span className="ml-2 text-brand font-medium" data-testid="team-shared-credits">
                        共享池 {t.shared_credits} 积分
                      </span>
                    )}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 shrink-0">
                  <button
                    onClick={() => useTeamPool(t.team_id)}
                    className={cn(
                      "btn-secondary text-xs h-8",
                      billingTeamId === t.team_id && "border-brand text-brand",
                    )}
                    data-testid="use-team-pool"
                  >
                    {billingTeamId === t.team_id ? "扣费中" : "用团队池"}
                  </button>
                  <button
                    onClick={() => setInvite({ teamId: t.team_id, value: "" })}
                    className="btn-secondary text-xs h-8"
                  >
                    <UserPlus className="w-3.5 h-3.5" /> 邀请
                  </button>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {(t.members || []).map((m, i) => (
                  <span key={`${m.user_id}-${i}`} className={cn(
                    "inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] border",
                    m.status === "pending" ? "border-amber-500/30 text-amber-600 bg-amber-500/5" : "border-cosmic-border text-text-secondary"
                  )}>
                    <Mail className="w-3 h-3" />
                    {m.invite_username || m.invite_email || `user#${m.user_id}`}
                    <span className="opacity-60">· {m.role}</span>
                  </span>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-cosmic-border/60 pt-3">
                <input
                  type="number"
                  min={1}
                  value={fundAmount}
                  onChange={(e) => setFundAmount(e.target.value)}
                  className="input-cosmic h-8 w-24 text-xs"
                  placeholder="积分"
                />
                <button
                  onClick={() => fundTeam(t.team_id)}
                  disabled={funding}
                  className="btn-primary h-8 text-xs"
                  data-testid="fund-team-pool"
                >
                  {funding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "充值团队池"}
                </button>
                <button
                  onClick={() => buySeats(t.team_id)}
                  disabled={buyingSeats}
                  className="btn-ghost h-8 text-xs"
                >
                  {buyingSeats ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "购买额外席位"}
                </button>
              </div>
              {invite?.teamId === t.team_id && (
                <div className="mt-3 flex gap-2">
                  <input
                    value={invite.value}
                    onChange={(e) => setInvite({ ...invite, value: e.target.value })}
                    placeholder="邮箱或用户名"
                    className="flex-1 input-cosmic h-9 text-sm"
                  />
                  <button onClick={doInvite} disabled={inviting} className="btn-primary h-9 text-sm">
                    {inviting ? <Loader2 className="w-4 h-4 animate-spin" /> : "发送"}
                  </button>
                  <button onClick={() => setInvite(null)} className="btn-ghost h-9 text-sm">取消</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      {billingTeamId && (
        <p className="text-center text-xs text-text-tertiary mt-4">
          当前创作扣费来源：团队池
          <button onClick={clearTeamPool} className="ml-2 text-brand hover:underline">改回个人账户</button>
        </p>
      )}
    </div>
  );
}
