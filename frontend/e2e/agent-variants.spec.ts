import { test, expect } from "@playwright/test";
import { E2E_GUEST_ID, waitForBackend } from "./helpers";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/+$/, "");

test.beforeAll(async () => {
  await waitForBackend();
});

test.describe("Director 变体并行 dry-run", () => {
  test("variants/run → 轮询 batch 完成", async ({ request }) => {
    test.setTimeout(120_000);

    const brief = "15秒咖啡产品竖屏宣传片，电影级画质";
    const runRes = await request.post(`${API_BASE}/director/variants/run`, {
      headers: { "X-Guest-Id": E2E_GUEST_ID, "Content-Type": "application/json" },
      data: {
        brief,
        duration: 15,
        minimal: true,
        n: 2,
        dry_run: true,
      },
    });
    expect(runRes.ok()).toBeTruthy();
    const runBody = await runRes.json();
    expect(runBody.dry_run).toBe(true);
    expect(runBody.batch_id).toBeTruthy();
    expect(runBody.count).toBeGreaterThanOrEqual(2);

    const batchId = runBody.batch_id as string;
    const deadline = Date.now() + 90_000;
    let lastStatus = "running";
    while (Date.now() < deadline) {
      const prog = await request.get(`${API_BASE}/director/variants/progress/${batchId}`, {
        headers: { "X-Guest-Id": E2E_GUEST_ID },
      });
      expect(prog.ok()).toBeTruthy();
      const body = await prog.json();
      lastStatus = body.status;
      if (body.done) {
        expect(body.count).toBeGreaterThanOrEqual(2);
        expect(body.items?.length).toBeGreaterThanOrEqual(2);
        for (const item of body.items || []) {
          expect(item.done).toBe(true);
        }
        return;
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
    throw new Error(`variants batch did not complete in time (last status: ${lastStatus})`);
  });
});
