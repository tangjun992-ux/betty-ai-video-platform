import { test, expect } from "@playwright/test";
import { waitForBackend } from "./helpers";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/+$/, "");

test.beforeAll(async () => {
  await waitForBackend();
});

test.describe("定价 · dev-grant Checkout", () => {
  test("积分包 checkout 直发（无 Stripe key）", async ({ request }) => {
    const guestId = `e2e-pricing-${Date.now()}`;
    const summaryBefore = await request.get(`${API_BASE}/billing/summary`, {
      headers: { "X-Guest-Id": guestId },
    });
    expect(summaryBefore.ok()).toBeTruthy();
    const before = await summaryBefore.json();

    const res = await request.post(`${API_BASE}/billing/checkout`, {
      headers: { "X-Guest-Id": guestId, "Content-Type": "application/json" },
      data: { kind: "pack", id: "pack_mini", cycle: "monthly", quantity: 1 },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.mode).toBe("dev");
    expect(body.success).toBe(true);
    expect(body.credits_added).toBeGreaterThan(0);

    const summaryAfter = await request.get(`${API_BASE}/billing/summary`, {
      headers: { "X-Guest-Id": guestId },
    });
    const after = await summaryAfter.json();
    expect(after.available_credits).toBeGreaterThan(before.available_credits ?? 0);
  });
});

test.describe("定价页", () => {
  test("定价页加载并展示套餐", async ({ page }) => {
    await page.goto("/pricing");
    const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
    if (await accept.isVisible().catch(() => false)) await accept.click();
    await expect(page.getByText(/Starter|Starter/i).first()).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/Credits|积分/i).first()).toBeVisible();
  });
});
