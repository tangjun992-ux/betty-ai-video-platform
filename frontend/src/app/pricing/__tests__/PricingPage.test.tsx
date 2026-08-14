import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import PricingPage from "../page";
import { LocaleProvider } from "@/i18n/LocaleProvider";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/pricing",
  useSearchParams: () => new URLSearchParams(),
}));

function wrap(ui: ReactNode) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("Pricing Stripe honesty", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => ({
        api_key_configured: false,
        subscription_ready: false,
        honesty: "本环境未注入 Stripe Key / Price，订阅按钮无法真实收款。",
      }),
    })));
  });

  it("shows unpaid environment banner", async () => {
    wrap(<PricingPage />);
    await waitFor(() => {
      expect(screen.getByTestId("pricing-stripe-honesty")).toBeInTheDocument();
    });
  });
});
