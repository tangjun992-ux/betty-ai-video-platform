import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Film, Image as ImageIcon } from "lucide-react";
import { AgentScenarioBoard } from "../AgentScenarioBoard";

describe("AgentScenarioBoard", () => {
  it("splits Video / Image and does not invent a tools section", () => {
    render(
      <AgentScenarioBoard
        items={[
          { id: "product_ad", icon: Film, cat: "视频", title: "产品广告", desc: "投放" },
          { id: "ai_portrait", icon: ImageIcon, cat: "图片", title: "AI 写真", desc: "头像" },
        ]}
        onSelect={vi.fn()}
        titleOf={(s) => s.title}
        descOf={(s) => s.desc}
        catOf={(c) => c}
        videoLabel="视频"
        imageLabel="图片"
      />,
    );
    expect(screen.getByTestId("agent-try-video")).toBeTruthy();
    expect(screen.getByTestId("agent-try-image")).toBeTruthy();
    expect(screen.queryByTestId("agent-try-utility")).toBeNull();
    expect(screen.getByText("产品广告")).toBeTruthy();
    expect(screen.getByText("AI 写真")).toBeTruthy();
  });
});
