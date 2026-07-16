// API client for the AI Video Platform backend

// Normalize: tolerate NEXT_PUBLIC_API_URL set with or without the /api/v1 suffix
const _raw = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/+$/, "");
export const API_BASE = _raw.endsWith("/api/v1") ? _raw : `${_raw}/api/v1`;

export function trackOnboarding(event: string): void {
  if (typeof window === "undefined") return;
  fetch(`${API_BASE}/events/onboarding`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event }),
    keepalive: true,
  }).catch(() => {});
}

/** Read the persisted JWT from the zustand auth-store (localStorage). */
export function authToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem("auth-store");
    if (!raw) return null;
    return JSON.parse(raw)?.state?.token ?? null;
  } catch {
    return null;
  }
}

/** Stable per-browser guest id for isolated anonymous accounts. */
export function guestId(): string {
  if (typeof window === "undefined") return "";
  let id = localStorage.getItem("betty-guest-id");
  if (!id) {
    id = (typeof crypto !== "undefined" && crypto.randomUUID)
      ? crypto.randomUUID().replace(/-/g, "")
      : `g${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem("betty-guest-id", id);
    document.cookie = `betty_guest_id=${encodeURIComponent(id)};path=/;max-age=31536000;SameSite=Lax`;
  }
  return id;
}

/** Active team pool for shared credit deduction (X-Team-Id). */
export function activeTeamId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("betty-active-team-id");
}

export function setActiveTeamId(teamId: string | null): void {
  if (typeof window === "undefined") return;
  if (teamId) localStorage.setItem("betty-active-team-id", teamId);
  else localStorage.removeItem("betty-active-team-id");
}

/** Headers for API calls — bearer when logged in, else stable guest id. */
export function apiAuthHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  const token = authToken();
  if (token) {
    if (!headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
  } else if (typeof window !== "undefined" && !headers.has("X-Guest-Id")) {
    headers.set("X-Guest-Id", guestId());
  }
  const teamId = activeTeamId();
  if (teamId && !headers.has("X-Team-Id")) {
    headers.set("X-Team-Id", teamId);
  }
  return headers;
}

/** Install a one-time global fetch interceptor that attaches auth/guest headers. */
export function installAuthFetch() {
  if (typeof window === "undefined") return;
  if ((window as any).__betty_auth_fetch) return;
  const orig = window.fetch.bind(window);
  (window as any).__betty_auth_fetch = true;
  window.fetch = (input: RequestInfo | URL, init: RequestInit = {}) => {
    try {
      const url = typeof input === "string" ? input : (input instanceof URL ? input.href : (input as Request).url);
      if (url && url.includes("/api/v1/")) {
        const headers = apiAuthHeaders(init.headers || (input instanceof Request ? input.headers : undefined));
        init = { ...init, headers };
      }
    } catch {}
    return orig(input as any, init);
  };
}

const FETCH_TIMEOUT_MS = 15000; // 15s per request

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = FETCH_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

// ─── Auth API ──────────────────────────────────────────

export interface AuthUser {
  id: string;
  email: string;
  name?: string;
  credits: number;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface RegisterResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "登录失败" }));
    throw new Error(err.detail || `登录失败: ${res.status}`);
  }
  return res.json();
}

export async function register(
  username: string,
  email: string,
  password: string
): Promise<RegisterResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "注册失败" }));
    throw new Error(err.detail || `注册失败: ${res.status}`);
  }
  return res.json();
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  type: "image" | "video";
  description: string;
  max_resolution: string;
  avg_latency_s: number;
  cost_per_request: number;
  styles: string[];
  available: boolean;
  status?: string;
  display_name?: string;
}

export interface GenerateRequest {
  prompt: string;
  media_type?: "image" | "video" | "auto";
  model?: string;
  quality?: "fast" | "balanced" | "high";
  resolution?: string;
  duration?: number;
  count?: number;
  style?: string;
  enhance_prompt?: boolean;
  image_url?: string;
  seed?: number;
}

export interface GenerateResponse {
  task_id: string;
  status: string;
  estimated_model: string;
  estimated_time_seconds: number;
  estimated_cost_credits: number;
  poll_url: string;
  enhanced_prompt?: string;
  routing_info?: Record<string, unknown>;
}

export interface TaskProgress {
  task_id: string;
  status: string;
  progress?: number;
  current_stage?: string;
  model?: string;
  started_at?: string;
  estimated_completion?: string;
}

export interface TaskResult {
  task_id: string;
  status: string;
  progress?: number;
  current_stage?: string;
  result_url?: string;
  results?: Array<{ url: string; type: string; model?: string; thumbnail?: string; seed?: number }>;
  cost_credits?: number;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  parameters?: Record<string, any>;
}

/** Submit a generation request to the backend */
export async function submitGeneration(req: GenerateRequest): Promise<GenerateResponse> {
  const res = await fetchWithTimeout(`${API_BASE}/generate/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: req.prompt,
      media_type: req.media_type || "auto",
      model: req.model || "auto",
      quality: req.quality || "balanced",
      resolution: req.resolution || "1080x1080",
      duration: req.duration || 5,
      count: req.count || 1,
      style: req.style || null,
      enhance_prompt: req.enhance_prompt ?? true,
      image_url: req.image_url || null,
      ...(req.seed != null ? { seed: req.seed } : {}),
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `生成请求失败: ${res.status}`);
  }
  return res.json();
}

/** Poll task status — returns TaskResult when complete, TaskProgress otherwise */
export async function getTaskStatus(taskId: string, timeoutMs = 15000): Promise<TaskProgress | TaskResult> {
  const res = await fetchWithTimeout(`${API_BASE}/tasks/${taskId}`, {}, timeoutMs);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `查询任务失败: ${res.status}`);
  }
  return res.json();
}

/** Upload an image and return the URL */
export async function uploadImage(file: File): Promise<{ url: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw new Error(`上传失败: ${res.status}`);
  }
  return res.json();
}

/** Enhance a prompt into a richer professional version */
export async function enhancePrompt(
  prompt: string,
  mediaType: string = "auto",
  style?: string
): Promise<{ original: string; enhanced: string; additions: string[]; changed: boolean }> {
  const res = await fetch(`${API_BASE}/generate/enhance`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, media_type: mediaType, style: style || null }),
  });
  if (!res.ok) throw new Error(`优化失败: ${res.status}`);
  return res.json();
}

/** Generate a voiceover (TTS) from text — real provider when keys configured; demo tone otherwise */
export async function generateSpeech(
  text: string,
  voice: string = "Rachel"
): Promise<{ url: string; media_type: string; model: string; cost?: number; demo?: boolean }> {
  const res = await fetch(`${API_BASE}/generate/speech`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice }),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `配音失败: ${res.status}`);
  }
  return res.json();
}

/** Run an image tool (edit / upscale / bg-remove / extend) — real KIE models */
export async function editImageTool(params: {
  operation: "edit" | "upscale" | "bg-remove" | "extend";
  file?: File | null;
  imageUrl?: string;
  prompt?: string;
  factor?: string;
  ratio?: string;
}): Promise<{ url: string; source_url?: string; media_type: string; model: string; operation?: string; cost?: number }> {
  const fd = new FormData();
  fd.append("operation", params.operation);
  if (params.file) fd.append("image_file", params.file);
  if (params.imageUrl) fd.append("image_url", params.imageUrl);
  if (params.prompt) fd.append("prompt", params.prompt);
  if (params.factor) fd.append("factor", params.factor);
  if (params.ratio) fd.append("ratio", params.ratio);
  const res = await fetch(`${API_BASE}/generate/edit`, { method: "POST", body: fd });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `处理失败: ${res.status}`);
  }
  return res.json();
}

// ─── Developer API keys ─────────────────────────────────
export async function listApiKeys(): Promise<{ keys: any[] }> {
  const res = await fetch(`${API_BASE}/developer/keys`);
  if (!res.ok) throw new Error(`加载密钥失败: ${res.status}`);
  return res.json();
}
export async function createApiKeyPlatform(name: string): Promise<any> {
  const res = await fetch(`${API_BASE}/developer/keys`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }),
  });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `创建失败: ${res.status}`); }
  return res.json();
}
export async function revokeApiKey(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/developer/keys/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`吊销失败: ${res.status}`);
}

// ─── Billing (积分/套餐) ────────────────────────────────
export async function getBillingSummary(): Promise<any> {
  const res = await fetch(`${API_BASE}/billing/summary`);
  if (!res.ok) throw new Error(`加载余额失败: ${res.status}`);
  return res.json();
}
export async function getCreditPacks(): Promise<{ packs: any[] }> {
  const res = await fetch(`${API_BASE}/billing/credit-packs`);
  if (!res.ok) throw new Error(`加载积分包失败: ${res.status}`);
  return res.json();
}
export async function getTransactions(limit = 50): Promise<{ transactions: any[] }> {
  const res = await fetch(`${API_BASE}/billing/transactions?limit=${limit}`);
  if (!res.ok) throw new Error(`加载流水失败: ${res.status}`);
  return res.json();
}
export async function getUsage(days = 30): Promise<any> {
  const res = await fetch(`${API_BASE}/billing/usage?days=${days}`);
  if (!res.ok) throw new Error(`加载用量失败: ${res.status}`);
  return res.json();
}
export async function refundOrder(orderNo: string): Promise<any> {
  const res = await fetch(`${API_BASE}/billing/refund/${orderNo}`, { method: "POST" });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `退款失败: ${res.status}`); }
  return res.json();
}
export async function getReceipt(orderNo: string): Promise<any> {
  const res = await fetch(`${API_BASE}/billing/receipt/${orderNo}`);
  if (!res.ok) throw new Error(`加载收据失败: ${res.status}`);
  return res.json();
}
export async function checkout(kind: "plan" | "pack", id: string, cycle: "monthly" | "yearly" = "monthly"): Promise<any> {
  const res = await fetch(`${API_BASE}/billing/checkout`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, id, cycle }),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `结算失败: ${res.status}`);
  }
  const data = await res.json();
  if (data.mode === "stripe" && data.checkout_url) {
    window.location.href = data.checkout_url;
  } else {
    try { window.dispatchEvent(new Event("betty:credits")); } catch {}
  }
  return data;
}

// ─── QR Payments (微信支付 / 支付宝) ────────────────────
export async function getPayMethods(): Promise<{ methods: Record<string, { live: boolean }>; usd_to_cny: number }> {
  const res = await fetch(`${API_BASE}/billing/pay/methods`);
  if (!res.ok) throw new Error(`加载支付方式失败: ${res.status}`);
  return res.json();
}
export async function createPayOrder(kind: "plan" | "pack", id: string, method: "wechat" | "alipay", cycle: "monthly" | "yearly" = "monthly"): Promise<any> {
  const res = await fetch(`${API_BASE}/billing/pay/create`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, id, method, cycle }),
  });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `下单失败: ${res.status}`); }
  return res.json();
}
export async function getPayStatus(orderNo: string): Promise<any> {
  const res = await fetch(`${API_BASE}/billing/pay/status/${orderNo}`);
  if (!res.ok) throw new Error(`查询失败: ${res.status}`);
  return res.json();
}
export async function mockConfirmPay(orderNo: string): Promise<any> {
  const res = await fetch(`${API_BASE}/billing/pay/mock-confirm/${orderNo}`, { method: "POST" });
  if (!res.ok) throw new Error(`确认失败: ${res.status}`);
  return res.json();
}

// ─── Projects (作品集) ──────────────────────────────────
export interface ProjectItemRef { item_id: string; url: string; thumbnail?: string | null; media_type: string; title?: string | null; }
export interface ProjectDTO {
  id: string;
  name: string;
  description?: string | null;
  cover?: string | null;
  item_count: number;
  items: ProjectItemRef[];
  visibility?: "private" | "team" | "public";
  team_id?: string | null;
  owner_user_id?: number;
  created_at: string;
  updated_at: string;
}

export async function listProjects(): Promise<{ projects: ProjectDTO[] }> {
  const res = await fetch(`${API_BASE}/projects/`);
  if (!res.ok) throw new Error(`加载项目失败: ${res.status}`);
  return res.json();
}
export async function createProject(
  name: string,
  description?: string,
  opts?: { visibility?: string; team_id?: string },
): Promise<ProjectDTO> {
  const res = await fetch(`${API_BASE}/projects/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      description,
      visibility: opts?.visibility || "private",
      team_id: opts?.team_id,
    }),
  });
  if (!res.ok) throw new Error(`创建项目失败: ${res.status}`);
  return res.json();
}
export async function updateProject(
  id: string,
  patch: { name?: string; description?: string; visibility?: string; team_id?: string | null },
): Promise<ProjectDTO> {
  const res = await fetch(`${API_BASE}/projects/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error(`更新项目失败: ${res.status}`);
  return res.json();
}
export async function getProject(id: string): Promise<ProjectDTO> {
  const res = await fetch(`${API_BASE}/projects/${id}`);
  if (!res.ok) throw new Error(`项目不存在: ${res.status}`);
  return res.json();
}
export async function addProjectItem(id: string, item: ProjectItemRef): Promise<ProjectDTO> {
  const res = await fetch(`${API_BASE}/projects/${id}/items`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(item) });
  if (!res.ok) throw new Error(`添加失败: ${res.status}`);
  return res.json();
}
export async function removeProjectItem(id: string, itemId: string): Promise<ProjectDTO> {
  const res = await fetch(`${API_BASE}/projects/${id}/items/${encodeURIComponent(itemId)}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`移除失败: ${res.status}`);
  return res.json();
}
export async function deleteProject(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`删除失败: ${res.status}`);
}

/** List content-library items (uploads + generated) */
export async function listLibrary(params: { media_type?: string; source?: string; limit?: number } = {}): Promise<{ items: any[]; total: number; counts: any }> {
  const q = new URLSearchParams();
  if (params.media_type) q.set("media_type", params.media_type);
  if (params.source) q.set("source", params.source);
  q.set("limit", String(params.limit ?? 60));
  const res = await fetch(`${API_BASE}/library/?${q.toString()}`, { headers: apiAuthHeaders() });
  if (!res.ok) throw new Error(`加载素材库失败: ${res.status}`);
  return res.json();
}

export interface TimelineProject {
  id: string;
  name: string;
  clips: {
    url: string;
    start?: number;
    end?: number;
    volume?: number;
    transition?: string;
    label?: string;
  }[];
  settings?: {
    narration_url?: string | null;
    with_audio?: boolean;
    transition?: string;
    export_preset?: string;
    subtitle_track?: { text: string; start?: number; end?: number }[];
  };
  created_at?: string;
  updated_at?: string;
}

export async function listTimelineProjects(): Promise<{ projects: TimelineProject[]; total: number }> {
  const res = await fetch(`${API_BASE}/timeline/projects`, { headers: apiAuthHeaders() });
  if (!res.ok) throw new Error(`加载时间线项目失败: ${res.status}`);
  return res.json();
}

export async function getTimelineProject(id: string): Promise<TimelineProject> {
  const res = await fetch(`${API_BASE}/timeline/projects/${encodeURIComponent(id)}`, { headers: apiAuthHeaders() });
  if (!res.ok) throw new Error(`加载项目失败: ${res.status}`);
  return res.json();
}

export interface SaveTimelineProjectResponse {
  id: string;
  name: string;
  clip_count: number;
  total_duration: number;
  created_at: string;
  updated_at: string;
}

export async function saveTimelineProject(payload: {
  id?: string;
  name: string;
  clips: TimelineProject["clips"];
  settings?: TimelineProject["settings"];
}): Promise<SaveTimelineProjectResponse> {
  const res = await fetch(`${API_BASE}/timeline/projects`, {
    method: "POST",
    headers: apiAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `保存项目失败: ${res.status}`);
  }
  return res.json();
}

/** Parse SubRip (.srt) content into timeline subtitle cues */
export async function parseTimelineSrt(content: string): Promise<{
  subtitle_track: { text: string; start: number; end: number }[];
  cue_count: number;
}> {
  const res = await fetch(`${API_BASE}/timeline/subtitles/parse`, {
    method: "POST",
    headers: apiAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    const detail = e.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message || `解析失败: ${res.status}`);
  }
  return res.json();
}

/** Compose an ordered list of clips into one film (timeline editor) */
export async function composeTimeline(
  clips: {
    url: string;
    start?: number;
    end?: number;
    volume?: number;
    transition?: string;
  }[],
  opts: {
    narration_url?: string;
    with_audio?: boolean;
    transition?: string;
    subtitle_track?: { text: string; start?: number; end?: number }[];
    export_preset?: string;
  } = {},
): Promise<{
  url: string;
  thumbnail: string;
  clip_count: number;
  transition?: string;
  export_preset?: string;
}> {
  const res = await fetch(`${API_BASE}/timeline/compose`, {
    method: "POST",
    headers: apiAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      clips,
      narration_url: opts.narration_url ?? null,
      with_audio: opts.with_audio ?? true,
      transition: opts.transition ?? "cut",
      subtitle_track: opts.subtitle_track ?? [],
      export_preset: opts.export_preset ?? null,
    }),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || `合成失败: ${res.status}`);
  }
  return res.json();
}

/** Like (or undo) a gallery item — real persisted community reaction */
export async function likeGalleryItem(itemId: string, undo = false): Promise<{ likes: number; liked: boolean }> {
  const res = await fetch(`${API_BASE}/gallery/${encodeURIComponent(itemId)}/like?undo=${undo}`, { method: "POST" });
  if (!res.ok) throw new Error(`点赞失败: ${res.status}`);
  return res.json();
}

/** Report a gallery item (community moderation) */
export async function reportGalleryItem(itemId: string): Promise<{ reports: number; hidden: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/gallery/${encodeURIComponent(itemId)}/report`, { method: "POST" });
  if (!res.ok) throw new Error(`举报失败: ${res.status}`);
  return res.json();
}

/** Explicitly publish a completed task for public share / explore listing */
export async function publishShare(taskId: string): Promise<{ task_id: string; share_public: boolean; share_path: string }> {
  const res = await fetch(`${API_BASE}/gallery/share/${encodeURIComponent(taskId)}/publish`, {
    method: "POST",
    headers: apiAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `公开分享失败: ${res.status}`);
  }
  return res.json();
}

/** Revoke public share for a task */
export async function unpublishShare(taskId: string): Promise<{ task_id: string; share_public: boolean }> {
  const res = await fetch(`${API_BASE}/gallery/share/${encodeURIComponent(taskId)}/unpublish`, {
    method: "POST",
    headers: apiAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `取消公开失败: ${res.status}`);
  }
  return res.json();
}

/** Analyze a prompt without submitting — accepts string or object */
export async function analyzePrompt(input: string | { prompt: string; media_type?: string; quality?: string; model?: string }) {
  const body = typeof input === "string" ? { prompt: input } : input;
  const res = await fetch(`${API_BASE}/generate/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`分析失败: ${res.status}`);
  return res.json();
}

/** List user tasks with optional status filter */
export async function listTasks(token?: string, status?: string, limit = 50, offset = 0) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}/tasks/?${params}`, { headers });
  if (!res.ok) throw new Error(`获取任务列表失败: ${res.status}`);
  return res.json();
}

/** Fetch available models from backend.
 *  Defaults to verified/production-ready models only; pass includeBeta to also
 *  surface lab models (kept separate in the `beta` field). */
export async function listModels(includeBeta = false): Promise<{
  models: ModelInfo[]; active?: ModelInfo[]; beta?: ModelInfo[];
  active_count?: number; beta_count?: number;
}> {
  const q = includeBeta ? "?include_beta=true" : "?status=active";
  const res = await fetch(`${API_BASE}/models/${q}`);
  if (!res.ok) throw new Error(`获取模型列表失败: ${res.status}`);
  return res.json();
}

// ─── Settings API ──────────────────────────────────────────

export interface SettingsProfile {
  id: number;
  username: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  role: string;
  is_active: boolean;
  created_at: string | null;
}

export interface UserPreferences {
  default_model: string;
  default_quality: string;
  default_resolution: string;
  language: string;
  theme: string;
  auto_enhance_prompt: boolean;
  save_history: boolean;
}

export interface NotificationSettings {
  email_task_complete: boolean;
  email_weekly_digest: boolean;
  email_promotions: boolean;
  push_task_complete: boolean;
  push_credits_low: boolean;
}

export interface BillingInfo {
  credits: number;
  daily_credits: number;
  daily_credits_max: number;
  total_spent: number;
  total_tasks: number;
  total_purchased: number;
  plan: string;
  recent_transactions: Array<{
    id: number;
    type: string;
    amount: number;
    description: string;
    created_at: string | null;
  }>;
}

export interface ApiKeyInfo {
  id: string;
  name: string;
  provider: string;
  key_preview: string;
  created_at: string | null;
}

export interface SettingsResponse {
  profile: SettingsProfile;
  preferences: UserPreferences;
  notifications: NotificationSettings;
  billing: BillingInfo;
  api_keys: ApiKeyInfo[];
}

export interface SaveSettingsRequest {
  profile?: { display_name?: string; avatar_url?: string; email?: string };
  preferences?: Partial<UserPreferences>;
  notifications?: Partial<NotificationSettings>;
}

/** Get all settings */
export async function getSettings(token: string): Promise<SettingsResponse> {
  const res = await fetch(`${API_BASE}/settings`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`获取设置失败: ${res.status}`);
  return res.json();
}

/** Save settings */
export async function saveSettings(token: string, data: SaveSettingsRequest) {
  const res = await fetch(`${API_BASE}/settings`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "保存失败" }));
    throw new Error(err.detail || "保存设置失败");
  }
  return res.json();
}

/** Add API key */
export async function createApiKey(
  token: string,
  data: { name: string; provider: string; key: string }
): Promise<{ message: string; key: ApiKeyInfo }> {
  const res = await fetch(`${API_BASE}/settings/api-keys`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("添加 API 密钥失败");
  return res.json();
}

/** Delete API key */
export async function deleteApiKey(token: string, keyId: string) {
  const res = await fetch(`${API_BASE}/settings/api-keys/${keyId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("删除 API 密钥失败");
  return res.json();
}

// Ensure guest/auth headers are attached before any page-level data fetch runs.
if (typeof window !== "undefined") {
  installAuthFetch();
}
