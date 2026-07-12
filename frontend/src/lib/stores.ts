import { create } from "zustand";
import { persist } from "zustand/middleware";

// ─── UI Store ──────────────────────────────────────────
interface UIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (v: boolean) => void;
  toggleSidebarCollapsed: () => void;
  setSidebarCollapsed: (v: boolean) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: false,
      sidebarCollapsed: false,
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setSidebarOpen: (v) => set({ sidebarOpen: v }),
      toggleSidebarCollapsed: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
    }),
    { name: "ui-store" }
  )
);

// ─── Creation Store ─────────────────────────────────────
export type MediaType = "image" | "video";
export type Quality = "fast" | "balanced" | "high";
export type PageTab = "prompt" | "edit" | "combine";

interface CreationState {
  // Active page
  activePage: "agent" | "image" | "video";
  setActivePage: (p: "agent" | "image" | "video") => void;

  // Prompt
  prompt: string;
  setPrompt: (p: string) => void;

  // Tab (for image page)
  activeTab: PageTab;
  setActiveTab: (t: PageTab) => void;

  // Model
  selectedModel: string;
  setSelectedModel: (m: string) => void;

  // Parameters
  quality: Quality;
  setQuality: (q: Quality) => void;
  style: string | null;
  setStyle: (s: string) => void;
  creativity: string;
  setCreativity: (c: string) => void;
  resolution: string;
  setResolution: (r: string) => void;
  aspectRatio: string;
  setAspectRatio: (r: string) => void;
  count: number;
  setCount: (n: number) => void;
  duration: number;
  setDuration: (n: number) => void;

  // Reference files
  referenceFiles: Array<{ file: File; preview: string; type: "image" | "video" | "audio" }>;
  addReference: (f: File, preview: string, type: "image" | "video" | "audio") => void;
  removeReference: (idx: number) => void;
  clearReferences: () => void;

  // History (recent prompts)
  recentPrompts: string[];
  addRecentPrompt: (p: string) => void;

  // Results
  results: Array<{ url: string; type: "image" | "video"; prompt: string; model: string; seed?: number }>;
  addResult: (r: { url: string; type: "image" | "video"; prompt: string; model: string; seed?: number }) => void;

  // Reset
  resetCreation: () => void;
}

export const useCreationStore = create<CreationState>()(
  persist(
    (set) => ({
      activePage: "image",
      setActivePage: (p) => set({ activePage: p }),

      prompt: "",
      setPrompt: (p) => set({ prompt: p }),

      activeTab: "prompt",
      setActiveTab: (t) => set({ activeTab: t }),

      selectedModel: "auto",
      setSelectedModel: (m) => set({ selectedModel: m }),

      quality: "balanced",
      setQuality: (q) => set({ quality: q }),
      style: null,
      setStyle: (s) => set({ style: s }),
      creativity: "balanced",
      setCreativity: (c) => set({ creativity: c }),
      resolution: "1080p",
      setResolution: (r) => set({ resolution: r }),
      aspectRatio: "1:1",
      setAspectRatio: (r) => set({ aspectRatio: r }),
      count: 1,
      setCount: (n) => set({ count: n }),
      duration: 5,
      setDuration: (n) => set({ duration: n }),

      referenceFiles: [],
      addReference: (file, preview, type) =>
        set((s) => ({ referenceFiles: [...s.referenceFiles, { file, preview, type }] })),
      removeReference: (idx) =>
        set((s) => ({ referenceFiles: s.referenceFiles.filter((_, i) => i !== idx) })),
      clearReferences: () => set({ referenceFiles: [] }),

      recentPrompts: [],
      addRecentPrompt: (p) =>
        set((s) => ({
          recentPrompts: [p, ...s.recentPrompts.filter((x) => x !== p)].slice(0, 20),
        })),

      results: [],
      addResult: (r) => set((s) => ({ results: [r, ...s.results].slice(0, 50) })),

      resetCreation: () =>
        set({
          prompt: "",
          activeTab: "prompt",
          selectedModel: "auto",
          quality: "balanced",
          style: null,
          creativity: "balanced",
          resolution: "1080p",
          aspectRatio: "1:1",
          count: 1,
          duration: 5,
          referenceFiles: [],
          recentPrompts: [],
          results: [],
        }),
    }),
    { name: "creation-store" }
  )
);

// ─── Toast Store ────────────────────────────────────────
export type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
}

interface ToastState {
  toasts: Toast[];
  addToast: (t: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastState>()((set) => ({
  toasts: [],
  addToast: (t) => {
    const id = Math.random().toString(36).slice(2, 9);
    set((s) => ({ toasts: [...s.toasts, { ...t, id }] }));
    const duration = t.duration ?? 4000;
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((x) => x.id !== id) }));
    }, duration);
  },
  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

// ─── Auth Store ─────────────────────────────────────────
interface AuthState {
  user: { id: string; email: string; name?: string; credits: number } | null;
  token: string | null;
  setUser: (u: AuthState["user"]) => void;
  setToken: (t: string | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setUser: (u) => set({ user: u }),
      setToken: (t) => set({ token: t }),
      logout: () => set({ user: null, token: null }),
    }),
    { name: "auth-store" }
  )
);

// ─── First-work onboarding (per user) ───────────────────
interface OnboardingRecord {
  started: boolean;
  completed: boolean;
  dismissed: boolean;
}

interface OnboardingState {
  records: Record<string, OnboardingRecord>;
  startFor: (userId: string) => void;
  completeFor: (userId: string) => void;
  dismissFor: (userId: string) => void;
}

const emptyOnboarding = (): OnboardingRecord => ({
  started: false, completed: false, dismissed: false,
});

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set) => ({
      records: {},
      startFor: (userId) => set((s) => ({
        records: {
          ...s.records,
          [userId]: { ...(s.records[userId] || emptyOnboarding()), started: true, dismissed: false },
        },
      })),
      completeFor: (userId) => set((s) => ({
        records: {
          ...s.records,
          [userId]: { started: true, completed: true, dismissed: false },
        },
      })),
      dismissFor: (userId) => set((s) => ({
        records: {
          ...s.records,
          [userId]: { ...(s.records[userId] || emptyOnboarding()), dismissed: true },
        },
      })),
    }),
    { name: "onboarding-store" },
  ),
);

// ─── ⌘K Command Palette Store ───────────────────────────
interface CmdKState {
  open: boolean;
  setOpen: (v: boolean) => void;
  toggle: () => void;
}

export const useCmdKStore = create<CmdKState>()((set) => ({
  open: false,
  setOpen: (v) => set({ open: v }),
  toggle: () => set((s) => ({ open: !s.open })),
}));
