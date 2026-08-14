import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import DashboardPage from "../page";
import { LocaleProvider } from "@/i18n/LocaleProvider";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/dashboard",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    enhancePrompt: vi.fn(async (p: string) => ({ original: p, enhanced: p + " · cinematic", changed: true })),
  };
});

function wrap(ui: ReactNode) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("Dashboard conversation home (Yapper P0)", () => {
  beforeEach(() => {
    push.mockReset();
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => ({ stats: { credits_remaining: 10, assets_generated: 0, recent_generations: 0, success_rate: 0, total_spent: 0 }, recent_items: [], models: [] }),
    })));
  });

  it("renders headline and four CTAs", () => {
    wrap(<DashboardPage />);
    expect(screen.getByTestId("dashboard-headline")).toBeInTheDocument();
    expect(screen.getByTestId("cta-help-prompt")).toBeInTheDocument();
    expect(screen.getByTestId("cta-create-content")).toBeInTheDocument();
    expect(screen.getByTestId("cta-help-ideate")).toBeInTheDocument();
    expect(screen.getByTestId("cta-generate-audio")).toBeInTheDocument();
    expect(screen.getByTestId("dashboard-prompt")).toBeInTheDocument();
  });

  it("Create Content routes to video with prompt", async () => {
    wrap(<DashboardPage />);
    fireEvent.change(screen.getByTestId("dashboard-prompt"), { target: { value: "电影感咖啡宣传片" } });
    fireEvent.click(screen.getByTestId("cta-create-content"));
    await waitFor(() => {
      expect(push).toHaveBeenCalled();
      const dest = String(push.mock.calls[0][0]);
      expect(dest).toContain("/create/video");
      expect(dest).toContain("prompt=");
    });
  });

  it("Help Ideate routes to agent with brief", async () => {
    wrap(<DashboardPage />);
    fireEvent.change(screen.getByTestId("dashboard-prompt"), { target: { value: "帮我构思一条短剧" } });
    fireEvent.click(screen.getByTestId("cta-help-ideate"));
    await waitFor(() => {
      const dest = String(push.mock.calls[0][0]);
      expect(dest.startsWith("/agent")).toBe(true);
      expect(dest).toContain("brief=");
    });
  });

  it("Generate Audio routes to audio with text", async () => {
    wrap(<DashboardPage />);
    fireEvent.change(screen.getByTestId("dashboard-prompt"), { target: { value: "欢迎来到 Betty" } });
    fireEvent.click(screen.getByTestId("cta-generate-audio"));
    await waitFor(() => {
      const dest = String(push.mock.calls[0][0]);
      expect(dest).toContain("/create/audio");
      expect(dest).toContain("text=");
    });
  });
});
