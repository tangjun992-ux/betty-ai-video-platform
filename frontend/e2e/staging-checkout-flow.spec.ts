import { test, expect } from "@playwright/test";
import { waitForBackend } from "./helpers";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/+$/, "");

test.beforeAll(async () => {
  await waitForBackend();
});

test.describe("Staging 收款链路", () => {
  test("dev checkout pack_mini 增加积分", async ({ request }) => {
    const guestId = `e2e-checkout-dev-${Date.now()}`;
    const beforeRes = await request.get(`${API_BASE}/billing/summary`, {
      headers: { "X-Guest-Id": guestId },
    });
    expect(beforeRes.ok()).toBeTruthy();
    const before = await beforeRes.json();

    const ck = await request.post(`${API_BASE}/billing/checkout`, {
      headers: { "X-Guest-Id": guestId, "Content-Type": "application/json" },
      data: { kind: "pack", id: "pack_mini", cycle: "monthly", quantity: 1 },
    });
    expect(ck.ok()).toBeTruthy();
    const ckBody = await ck.json();
    expect(ckBody.mode === "dev" || ckBody.mode === "stripe").toBeTruthy();

    const afterRes = await request.get(`${API_BASE}/billing/summary`, {
      headers: { "X-Guest-Id": guestId },
    });
    const after = await afterRes.json();
    if (ckBody.mode === "dev") {
      expect(after.credits).toBeGreaterThan(before.credits ?? 0);
    }
  });

  test("staging-checkout-smoke 端到端自测", async ({ request }) => {
    const guestId = `e2e-smoke-${Date.now()}`;
    const res = await request.post(`${API_BASE}/billing/staging-checkout-smoke`, {
      headers: { "X-Guest-Id": guestId },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.ok).toBe(true);
    expect(body.credits_delta).toBeGreaterThan(0);
    expect(["dev_grant", "stripe_webhook"]).toContain(body.mode);
  });
});
