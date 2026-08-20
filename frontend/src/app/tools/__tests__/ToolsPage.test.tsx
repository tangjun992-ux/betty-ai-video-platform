import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ToolsPage from "../page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/tools",
}));

describe("Tools studio hub", () => {
  it("groups Video / Image tools and never names the competitor", () => {
    render(<ToolsPage />);
    expect(screen.getByTestId("tools-video-section")).toBeTruthy();
    expect(screen.getByTestId("tools-image-section")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Video Tools" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /唇形同步/ }).getAttribute("href")).toBe("/create/lipsync");
    expect(screen.getByRole("link", { name: /背景移除/ }).getAttribute("href")).toBe("/create/bg-remove");
    expect(screen.queryByText(/Yapper-style/)).toBeNull();
  });
});
