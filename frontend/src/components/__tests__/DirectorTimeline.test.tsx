import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DirectorTimeline, TimelineShot, timelineProgressLabel } from "../DirectorTimeline";

describe("timelineProgressLabel", () => {
  it("names the running step as n/m, not a fake shot count", () => {
    expect(
      timelineProgressLabel("running", [
        { status: "done" },
        { status: "running" },
        { status: "pending" },
      ]),
    ).toBe("执行中 · 第 2/3 步");
  });

  it("is silent when idle or planned", () => {
    expect(timelineProgressLabel("planned", [{ status: "pending" }])).toBeUndefined();
  });
});

describe("DirectorTimeline", () => {
  it("renders a numbered rail with agent-timeline", () => {
    render(
      <DirectorTimeline>
        <TimelineShot index={0} total={2} status="pending">
          <div data-testid="agent-step">enhance</div>
        </TimelineShot>
        <TimelineShot index={1} total={2} status="pending">
          <div data-testid="agent-step">video</div>
        </TimelineShot>
      </DirectorTimeline>,
    );
    expect(screen.getByTestId("agent-timeline")).toBeTruthy();
    const indexes = screen.getAllByTestId("agent-shot-index");
    expect(indexes.map((el) => el.textContent)).toEqual(["01", "02"]);
    expect(screen.getAllByTestId("agent-step")).toHaveLength(2);
  });

  it("marks the running shot as current", () => {
    render(
      <DirectorTimeline progressLabel="执行中 · 第 2/2 步">
        <TimelineShot index={0} total={2} status="done">
          <div data-testid="agent-step">a</div>
        </TimelineShot>
        <TimelineShot index={1} total={2} status="running">
          <div data-testid="agent-step">b</div>
        </TimelineShot>
      </DirectorTimeline>,
    );
    expect(screen.getByTestId("agent-timeline-current")).toBeTruthy();
    expect(screen.getByTestId("agent-timeline-progress").textContent).toBe("执行中 · 第 2/2 步");
  });
});
