// API client for the AI Video Platform backend

// Normalize: tolerate NEXT_PUBLIC_API_URL set with or without the /api/v1 suffix
const _raw = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/+$/, "");
export const API_BASE = _raw.endsWith("/api/v1") ? _raw : `${_raw}/api/v1`;

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
  results?: Array<{ url: string; type: string; model?: string; thumbnail?: string }>;
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

/** Fetch available models from backend */
export async function listModels(): Promise<{ models: ModelInfo[] }> {
  const res = await fetch(`${API_BASE}/models/`);
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
