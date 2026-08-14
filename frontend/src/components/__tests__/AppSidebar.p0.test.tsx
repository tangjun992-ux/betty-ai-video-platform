import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppSidebar } from "@/components/AppSidebar";
import { LocaleProvider } from "@/i18n/LocaleProvider";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/dashboard",
  useSearchParams: () => new URLSearchParams(),
}));

describe("AppSidebar Yapper IA", () => {
  it("Home points at /dashboard and lists Explore Library Agent Image Video", () => {
    render(
      <LocaleProvider>
        <AppSidebar />
      </LocaleProvider>,
    );
    const home = screen.getAllByRole("link").find((a) => a.getAttribute("href") === "/dashboard");
    expect(home).toBeTruthy();
    expect(screen.getAllByRole("link").some((a) => a.getAttribute("href") === "/explore")).toBe(true);
    expect(screen.getAllByRole("link").some((a) => a.getAttribute("href") === "/library")).toBe(true);
    expect(screen.getAllByRole("link").some((a) => a.getAttribute("href") === "/agent")).toBe(true);
    expect(screen.getAllByRole("link").some((a) => a.getAttribute("href") === "/create/image")).toBe(true);
    expect(screen.getAllByRole("link").some((a) => a.getAttribute("href") === "/create/video")).toBe(true);
  });
});
