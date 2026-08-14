import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SessionChip } from "../SessionChip";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    listStudioSessions: vi.fn(async () => [
      { session_uid: "sess1", title: "广告片 A", intent: "video_create" },
    ]),
    createStudioSession: vi.fn(async () => ({
      session_uid: "sess-new",
      title: "新视频会话",
      intent: "video_create",
    })),
  };
});

describe("SessionChip", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({ sessions: [] }) })));
  });

  it("lists and binds a video session", async () => {
    const onChange = vi.fn();
    render(<SessionChip intent="video_create" value={null} onChange={onChange} />);
    expect(screen.getByTestId("session-chip")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("session-chip-toggle"));
    await waitFor(() => {
      expect(screen.getByTestId("session-chip-list")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("广告片 A"));
    expect(onChange).toHaveBeenCalledWith("sess1");
  });
});
