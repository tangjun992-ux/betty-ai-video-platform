import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StudioStage } from "../StudioStage";

describe("StudioStage", () => {
  it("renders cinematic empty canvas copy", () => {
    render(<StudioStage title="画面将出现在这里" hint="描述运镜" kind="video" />);
    expect(screen.getByTestId("studio-stage")).toBeTruthy();
    expect(screen.getByText("画面将出现在这里")).toBeTruthy();
  });
});
