import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DirectorMonitor, pickMonitorAsset } from "../DirectorMonitor";

describe("pickMonitorAsset", () => {
  const shots = [
    { type: "image", url: "/a.jpg", step: "hero" },
    { type: "video", url: "/b.mp4", step: "shot-1" },
    { final: true, type: "video", url: "/final.mp4", step: "compose" },
  ];

  it("shows the latest shot while running, not a fake final", () => {
    expect(pickMonitorAsset(shots, "running")?.url).toBe("/b.mp4");
  });

  it("prefers the final cut when done", () => {
    expect(pickMonitorAsset(shots, "done")?.url).toBe("/final.mp4");
  });
});

describe("DirectorMonitor", () => {
  it("empty planned state says the cut will land here", () => {
    render(<DirectorMonitor phase="planned" />);
    expect(screen.getByTestId("agent-monitor")).toBeTruthy();
    expect(screen.getByTestId("agent-monitor-empty")).toBeTruthy();
    expect(screen.getByText("成片将出现在这里")).toBeTruthy();
  });

  it("renders media when a shot exists", () => {
    render(
      <DirectorMonitor
        phase="running"
        progressLabel="执行中 · 第 2/3 步"
        mediaUrl="https://example.com/shot.mp4"
        kind="video"
        title="分镜 1"
      />,
    );
    expect(screen.getByTestId("agent-monitor-media")).toBeTruthy();
    expect(screen.getByTestId("agent-monitor-progress").textContent).toBe("执行中 · 第 2/3 步");
  });
});
