import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import FaceSwapPage from "../page";

describe("Face Swap template funnel", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => ({ demo_mode: true, real_generation_available: false, features: {} }),
    })));
  });
  it("renders eight viral templates without InsightFace claims", () => {
    render(<FaceSwapPage />);
    expect(screen.getByTestId("face-swap-templates")).toBeInTheDocument();
    expect(screen.getByTestId("face-swap-template-poster")).toBeInTheDocument();
    expect(screen.getByTestId("face-swap-template-shortcover")).toBeInTheDocument();
    expect(screen.getByTestId("face-swap-template-holiday")).toBeInTheDocument();
    expect(screen.getByText(/非 InsightFace/)).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("face-swap-template-cyber"));
    expect((screen.getByPlaceholderText(/可选：补充融合要求/) as HTMLTextAreaElement).value).toMatch(/cyberpunk/i);
  });
});
