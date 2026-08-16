import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { ReactNode } from "react";
import CreateVideoPage from "../page";
import { LocaleProvider } from "@/i18n/LocaleProvider";
import { useCreationStore } from "@/lib/stores";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/create/video",
  useSearchParams: () => new URLSearchParams(),
}));

function wrap(ui: ReactNode) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("Video Ideas fill composer (Yapper UX)", () => {
  beforeEach(() => {
    push.mockReset();
    useCreationStore.getState().resetCreation();
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => ({ active: [] }),
    })));
  });

  it("renders idea chips and fills the prompt instead of bouncing to Agent", () => {
    wrap(<CreateVideoPage />);
    expect(screen.getByTestId("video-ideas-row")).toBeInTheDocument();
    const ugc = screen.getByTestId("video-idea-ugc");
    fireEvent.click(ugc);
    const prompt = screen.getByTestId("video-prompt") as HTMLTextAreaElement;
    expect(prompt.value).toMatch(/竖屏|9:16|口播/);
    expect(push).not.toHaveBeenCalled();
  });

  it("keeps Agent as an optional refine path", () => {
    wrap(<CreateVideoPage />);
    fireEvent.click(screen.getByTestId("video-idea-product"));
    fireEvent.click(screen.getByTestId("video-ideas-open-agent"));
    expect(push).toHaveBeenCalled();
    const dest = String(push.mock.calls[0][0]);
    expect(dest).toContain("/agent");
    expect(dest).toContain("brief=");
  });
});
