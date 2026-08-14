import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import GalleryPage from "../page";

describe("Explore gallery P1", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      const u = String(url);
      if (u.includes("/gallery/stats")) {
        return { ok: true, json: async () => ({
          total_images: 2, total_videos: 1, total_credits_consumed: 10,
          seed_items: 2, community_items: 0,
          honesty: "含平台示例，非百万级社区资产。completed ≠ 公开。",
        }) };
      }
      return {
        ok: true,
        json: async () => ({
          items: [
            {
              id: "abc_0",
              task_id: "abc",
              prompt: "neon city",
              media_type: "image",
              model_used: "nano-banana",
              style: "cinematic",
              styles: ["cinematic"],
              resolution: "1080x1080",
              url: "https://cdn.example.com/a.png",
              thumbnail: "https://cdn.example.com/a.png",
              credits_cost: 2,
              created_at: "2026-08-14T00:00:00Z",
              username: "betty",
              avatar: "",
              likes: 1,
              remixes: 4,
              views: 8,
            },
          ],
          styles: [{ key: "all", label: "全部" }],
          total: 1,
        }),
      };
    }));
  });

  it("renders server search box and remix count", async () => {
    render(<GalleryPage />);
    expect(screen.getByTestId("explore-search")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("explore-honesty")).toBeInTheDocument();
    });
    fireEvent.change(screen.getByTestId("explore-search"), { target: { value: "neon" } });
    await waitFor(() => {
      const calls = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.map((c) => String(c[0]));
      expect(calls.some((u) => u.includes("q=neon"))).toBe(true);
    });
  });
});
