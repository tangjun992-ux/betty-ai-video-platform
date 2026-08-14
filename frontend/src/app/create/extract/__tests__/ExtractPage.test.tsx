import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ExtractPage from "../page";

describe("URL-to-Viral extract page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => ({
        mode: "heuristic",
        prompt: "cinematic coffee pour",
        style_tags: ["cinematic"],
        media_type_hint: "video",
        honesty: "TikTok 官方 oEmbed | local heuristic",
        social: { platform: "tiktok", title: "POV coffee", source: "tiktok_oembed" },
        viral: {
          placement: "tiktok",
          placement_label: "TikTok / 抖音",
          aspect: "9:16",
          duration_sec: 15,
          honesty: "结构来自平台投放规格 + 标题/封面元数据，不是原片逐帧分镜反推",
          beats: [
            { key: "hook", label: "钩子", t: 0, prompt: "opening hook" },
            { key: "body", label: "展开", t: 3, prompt: "mid beat" },
            { key: "cta", label: "收束", t: 12, prompt: "cta close" },
          ],
        },
        create_links: {
          image: "/create/image?prompt=cinematic",
          video: "/create/video?prompt=cinematic&shot=opening+hook&viral=1",
          agent: "/agent?brief=cinematic",
        },
      }),
    })));
  });

  it("shows honest oEmbed copy and viral beats after extract", async () => {
    render(<ExtractPage />);
    expect(screen.getByTestId("extract-url-honesty").textContent).toMatch(/官方 oEmbed/);
    fireEvent.change(screen.getByTestId("extract-url"), {
      target: { value: "https://www.tiktok.com/@demo/video/1" },
    });
    fireEvent.click(screen.getByTestId("extract-submit"));
    await waitFor(() => expect(screen.getByTestId("extract-viral-panel")).toBeInTheDocument());
    expect(screen.getByTestId("extract-viral-placement").textContent).toMatch(/9:16/);
    expect(screen.getByTestId("extract-viral-honesty").textContent).toMatch(/不是原片/);
    const toVideo = screen.getByTestId("extract-to-video");
    expect(toVideo.getAttribute("href")).toContain("/create/video");
    expect(toVideo.getAttribute("href")).toContain("shot=");
  });
});
