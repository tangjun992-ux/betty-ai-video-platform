import { test, expect } from "@playwright/test";
import { waitForBackend } from "./helpers";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/+$/, "");

test.beforeAll(async () => {
  await waitForBackend();
});

test.describe("Staging Go-Live 验收 API", () => {
  test("staging-report 含 next_steps 与 summary", async ({ request }) => {
    const res = await request.get(`${API_BASE}/system/staging-report`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.generated_at).toBeTruthy();
    expect(body.summary?.dimensions).toBeTruthy();
    expect(Array.isArray(body.next_steps)).toBe(true);
    expect(body.commands?.staging_check).toContain("staging_go_live_check");
  });

  test("go-live-readiness 与 billing staging 一致可达", async ({ request }) => {
    const [gl, stripe, wh, whSelf] = await Promise.all([
      request.get(`${API_BASE}/system/go-live-readiness`),
      request.get(`${API_BASE}/billing/staging-readiness`),
      request.get(`${API_BASE}/billing/stripe-webhook-check`),
      request.get(`${API_BASE}/billing/stripe-webhook-self-test`),
    ]);
    expect(gl.ok()).toBeTruthy();
    expect(stripe.ok()).toBeTruthy();
    expect(wh.ok()).toBeTruthy();
    expect(whSelf.ok()).toBeTruthy();
    const glBody = await gl.json();
    const stBody = await stripe.json();
    const whBody = await wh.json();
    const whSelfBody = await whSelf.json();
    expect(typeof glBody.revenue_ready).toBe("boolean");
    expect(typeof stBody.staging_ready).toBe("boolean");
    expect(whBody.endpoint_path).toBe("/api/v1/billing/stripe/webhook");
    expect(whBody.required_events).toContain("checkout.session.completed");
    expect(typeof whSelfBody.self_test_ok).toBe("boolean");
  });

  test("oidc discovery-check 可达", async ({ request }) => {
    const res = await request.get(`${API_BASE}/auth/oidc/discovery-check`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(typeof body.probe_ok).toBe("boolean");
    expect(body.staging?.checklist).toBeTruthy();
  });

  test("staging-acceptance 记分卡与 webhook 投递自测", async ({ request }) => {
    const [acceptance, deliver] = await Promise.all([
      request.get(`${API_BASE}/system/staging-acceptance`),
      request.post(`${API_BASE}/billing/stripe-webhook-deliver-test`),
    ]);
    expect(acceptance.ok()).toBeTruthy();
    const accBody = await acceptance.json();
    expect(typeof accBody.acceptance_ok).toBe("boolean");
    expect(Array.isArray(accBody.checks)).toBe(true);
    expect(accBody.checks.some((c: { id: string }) => c.id === "webhook_signature")).toBe(true);

    // deliver test requires whsec — may fail in dev without env; accept 200 with delivery_ok boolean
    if (deliver.ok()) {
      const dBody = await deliver.json();
      expect(typeof dBody.delivery_ok).toBe("boolean");
    }
  });
});
