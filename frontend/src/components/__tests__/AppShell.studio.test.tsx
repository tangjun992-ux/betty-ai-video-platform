import { describe, it, expect } from "vitest";
import { isStudioPath } from "../AppShell";

describe("studio path", () => {
  it("treats create/agent/explore as studio and home/pricing as marketing", () => {
    expect(isStudioPath("/create/video")).toBe(true);
    expect(isStudioPath("/agent")).toBe(true);
    expect(isStudioPath("/explore")).toBe(true);
    expect(isStudioPath("/")).toBe(false);
    expect(isStudioPath("/pricing")).toBe(false);
    expect(isStudioPath("/status")).toBe(false);
  });
});
