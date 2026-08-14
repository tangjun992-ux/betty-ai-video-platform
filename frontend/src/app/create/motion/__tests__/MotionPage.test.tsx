import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import MotionControlPage from "../page";

describe("Motion TTS narration honesty", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => ({ demo_mode: true, real_generation_available: false, features: {} }),
    })));
  });

  it("exposes optional TTS that is not a voice changer", () => {
    render(<MotionControlPage />);
    expect(screen.getByTestId("motion-voice-honesty")).toBeInTheDocument();
    expect(screen.getByTestId("motion-voice-honesty").textContent).toMatch(/不是实时变声/);
    fireEvent.click(screen.getByLabelText(/附加 TTS 旁白/));
    expect(screen.getByTestId("motion-voice-text")).toBeInTheDocument();
  });
});
