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

describe("Pricing Stripe honesty + Yapper limits table", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("stripe-status")) {
        return {
          ok: true,
          json: async () => ({
            api_key_configured: false,
            subscription_ready: false,
            honesty: "本环境未注入 Stripe Key / Price，订阅按钮无法真实收款。",
          }),
        };
      }
      if (url.includes("pricing/plans")) {
        return {
          ok: true,
          json: async () => ({
            limits_honesty: "并发与 PLAN_CONCURRENCY 同源；席位是套餐合同。未注入 Stripe Key 仍不能收款。",
            plans: [
              { id: "starter", concurrent_generations: 4, included_team_seats: 0, credits_per_month: 1000 },
              { id: "personal", concurrent_generations: 6, included_team_seats: 0, credits_per_month: 3000 },
              { id: "creator", concurrent_generations: 10, included_team_seats: 2, credits_per_month: 7000 },
              {
                id: "max",
                concurrent_generations: 40,
                included_team_seats: 7,
                credits_per_month: 22500,
                max_tiers: [
                  { credits: 15000, monthly: 99.99, yearly: 79.99 },
                  { credits: 22500, monthly: 149.99, yearly: 119.99 },
                ],
              },
            ],
          }),
        };
      }
      if (url.includes("credit-packs")) {
        return { ok: true, json: async () => ({ packs: [] }) };
      }
      return { ok: true, json: async () => ({}) };
    }));
  });

  it("shows unpaid environment banner", async () => {
    wrap(<PricingPage />);
    await waitFor(() => {
      expect(screen.getByTestId("pricing-stripe-honesty")).toBeInTheDocument();
    });
    expect(screen.getByTestId("pricing-max-slider")).toBeInTheDocument();
    expect(screen.getByTestId("pricing-credit-packs")).toBeInTheDocument();
  });

  it("renders Yapper-style limits comparison from API fields", async () => {
    wrap(<PricingPage />);
    await waitFor(() => {
      expect(screen.getByTestId("pricing-limits-table")).toBeInTheDocument();
    });
    expect(screen.getByTestId("pricing-limits-row-concurrent").textContent).toMatch(/4/);
    expect(screen.getByTestId("pricing-limits-row-concurrent").textContent).toMatch(/40/);
    expect(screen.getByTestId("pricing-limits-row-seats").textContent).toMatch(/2/);
    expect(screen.getByTestId("pricing-limits-row-seats").textContent).toMatch(/7/);
    expect(screen.getByTestId("pricing-card-limits-creator").textContent).toMatch(/10/);
    expect(screen.getByTestId("pricing-limits-honesty").textContent).toMatch(/不能收款|Stripe/);
  });
});
